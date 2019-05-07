import npyscreen
import os
import glob
import datetime
import time
import logging
from magnetic_poller.mag_poller import MagPoller
import curses
import json


class ManagerTUI(npyscreen.NPSAppManaged):
    filename = ""
    sample_size = "5"
    magnetic_buffer = []
    current_point = "1"
    usb_device = "/dev/ttyUSB0"
    data_dict = {}

    def onStart(self):
        self.filename = self.get_filename()
        self.addForm("MAIN", RegisterParamsForm, name="Parameter setup")
        self.addForm("MAG", LoggerForm, name="Magnetic point logger")

    def get_filename(self, output_location=""):
        """
        Define new log file filename
        :return:
        """
        if output_location == "":
            output_location = os.getcwd()

        files = [os.path.basename(x) for x in glob.glob(os.path.join(output_location, "*.json"))]

        exp_size = 0
        if len(files) > 0:
            exp_size = max([int(f.split('.')[0]) for f in files])

        filename = os.path.join(output_location, str(exp_size + 1) + ".point_data." +
                                str(datetime.datetime.now().strftime("%Y%m%d.%H%M%S")) + ".json")

        return filename


class RegisterParamsForm(npyscreen.Form):
    def afterEditing(self):
        self.parentApp.setNextForm('MAG')
        self.parentApp.filename = self.filename.value
        self.parentApp.sample_size = self.sample_size.value
        self.parentApp.usb_device = self.usb_device.value

        try:
            with open(self.parentApp.filename, 'r') as f:
                self.parentApp.data_dict = json.load(f)
        except:
            pass

        self.parentApp._Forms["MAG"].load_current_point_data()

    def create(self):
        self.filename = self.add(npyscreen.TitleFilenameCombo,
                                 name="Select or write the name of the filename to save the points to:",
                                 value=self.parentApp.filename)

        self.sample_size = self.add(npyscreen.TitleText,
                                    name="Sample size per point:",
                                    value=self.parentApp.sample_size)

        # noinspection PyAttributeOutsideInit
        self.usb_device = self.add(npyscreen.TitleText,
                                   name="USB device:",
                                   value=self.parentApp.usb_device)


class PointBox(npyscreen.BoxTitle):
    _contained_widget = npyscreen.TitleFixedText


class ScrollBoxRawData(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager


class ScrollBoxPointBuffer(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager


class ScrollBoxPointsData(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager


class LoggerForm(npyscreen.FormBaseNew):
    def init_logger(self):
        self.logger = logging.getLogger('mag_application')
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('mag.log')
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def create(self):
        self.init_logger()

        self.keypress_timeout = 2
        self.add_handlers({
            "^Q": self.exit_application,
            curses.KEY_RIGHT: self.go_next_pressed,
            curses.KEY_LEFT: self.go_back_pressed,
        })

        y, x = self.useable_space()

        self.pointBox = self.add(npyscreen.BoxTitle,
                                 name="Point data",
                                 max_width=(x // 2) - 2,
                                 max_height=(y // 2) - 2,
                                 editable=False,
                                 )

        self.labelCurrentPoint = self.add(npyscreen.TitleFixedText,
                                          value='- Current POINT 01 -',
                                          name=' ',
                                          begin_entry_at=1,
                                          use_two_lines=False,
                                          rely=self.pointBox.rely + 2,
                                          relx=self.pointBox.relx + 1,
                                          width=41,
                                          height=1,
                                          editable=True
                                          )

        self.goBack = self.add(npyscreen.ButtonPress,
                               relx=self.pointBox.relx + 1,
                               rely=self.pointBox.rely + 6,
                               name='Back')

        self.goBack.whenPressed = self.go_back_pressed

        self.goNext = self.add(npyscreen.ButtonPress,
                               relx=self.pointBox.relx + 1,
                               rely=self.pointBox.rely + 7,
                               name='Next')
        self.goNext.whenPressed = self.go_next_pressed

        self.obtainData = self.add(npyscreen.ButtonPress,
                                   relx=self.pointBox.relx + 1,
                                   rely=self.pointBox.rely + 8,
                                   name='Obtain magnetic data')
        self.obtainData.whenPressed = self.obtain_data_pressed

        self.current_file = self.add(npyscreen.TitleFixedText,
                                          value='Filename: {}'.format(self.parentApp.filename),
                                          name=' ',
                                          begin_entry_at=0,
                                     use_two_lines=False,
                                          relx=self.pointBox.relx + 3,
                                          rely=self.pointBox.rely + 11,
                                          width=60,
                                          editable=False
                                          )

        self.current_point_timestamp = self.add(npyscreen.TitleFixedText,
                                     value='Current point timestamp: -',
                                     name=' ',
                                     begin_entry_at=0,
                                                use_two_lines=False,
                                     relx=self.pointBox.relx + 3,
                                     rely=self.pointBox.rely + 12,
                                     width=60,
                                     editable=False
                                     )

        self.current_point_data_size = self.add(npyscreen.TitleFixedText,
                                     value='Current point data size: -',
                                     name=' ',
                                     begin_entry_at=0,
                                                use_two_lines=False,
                                     relx=self.pointBox.relx + 3,
                                     rely=self.pointBox.rely + 13,
                                     width=60,
                                     editable=False
                                     )

        self.scrollBoxPointBuffer = self.add(ScrollBoxPointBuffer, name="Point buffer", footer="No editable",
                                             editable=False,
                                             max_width=(x // 2) - 2,
                                             max_height=(y // 2) - 2,
                                             relx=(x // 2),
                                             rely=(y // 2) + 1
                                             )

        self.scrollBoxRawData = self.add(ScrollBoxRawData, name="Mag readings", footer="No editable",
                                         editable=False,
                                         max_width=(x // 2) - 2,
                                         max_height=(y // 2) - 2,
                                         rely=2,
                                         relx=(x // 2)
                                         )

        self.scrollBoxPointsData = self.add(ScrollBoxPointsData, name="Data points gathered", footer="No editable",
                                         editable=False,
                                         max_width=(x // 2) - 2,
                                         max_height=(y // 2) - 2,
                                         rely=(y // 2) + 1,
                                         relx=1
                                         )

        self.mag = MagPoller(device=self.parentApp.usb_device, is_continuous=True, fake_test_data=True, debug=False)
        self.mag.start()
        time.sleep(1)

    def load_current_point_data(self):
        self.scrollBoxPointsData.entry_widget.clearBuffer()
        self.scrollBoxPointBuffer.entry_widget.clearBuffer()

        c_timestamp = "-"
        c_data_size = 0

        if self.parentApp.current_point in self.parentApp.data_dict.keys():
            data_d = self.parentApp.data_dict
            curr_p = self.parentApp.current_point
            c_timestamp = data_d[curr_p]['timestamp']
            c_data_size = len(data_d[curr_p]['mag_data'])

            for e in data_d[curr_p]['mag_data']:
                self.scrollBoxPointsData.entry_widget.buffer([e])

        self.current_point_timestamp.value = 'Current point timestamp: {}'.format(c_timestamp)
        self.current_point_timestamp.display()

        self.current_point_data_size.value = 'Current point data size: {}'.format(c_data_size)
        self.current_point_data_size.display()

        self.scrollBoxPointsData.entry_widget.display()
        self.scrollBoxPointBuffer.entry_widget.display()

    def go_back_pressed(self):
        pint = int(self.parentApp.current_point)
        pint -= 1

        if pint > 0:
            self.parentApp.current_point = str(pint)

        self.labelCurrentPoint.value = '- Current POINT {} -'.format(self.parentApp.current_point)
        self.labelCurrentPoint.display()
        self.logger.debug('goBackPress :{}'.format(pint))
        self.load_current_point_data()

    def go_next_pressed(self):
        pint = int(self.parentApp.current_point)
        pint += 1

        self.parentApp.current_point = str(pint)
        self.labelCurrentPoint.value = '- Current POINT {} -'.format(self.parentApp.current_point)
        self.labelCurrentPoint.display()
        self.logger.debug('goNextPressed :{}'.format(pint))
        self.load_current_point_data()

    def obtain_data_pressed(self):
        self.scrollBoxPointBuffer.entry_widget.clearBuffer()

        point_data = []
        for i in xrange(int(self.parentApp.sample_size)):
            mag_values = self.mag.get_values()
            point_data.append(mag_values)
            self.scrollBoxPointBuffer.entry_widget.buffer([" ".join(["{:.2f}".format(i) for i in mag_values])])
            self.scrollBoxPointBuffer.display()
            time.sleep(0.5)

        if self.parentApp.current_point not in self.parentApp.data_dict.keys():
            self.parentApp.data_dict[str(self.parentApp.current_point)] = {}

        self.parentApp.data_dict[str(self.parentApp.current_point)] = {
            'timestamp': str(datetime.datetime.now().strftime("%Y/%m/%d.%H:%M:%S")),
            'mag_data': point_data
        }

        self.logger.debug('self.parentApp.data_dict:{}'.format(self.parentApp.data_dict))

        with open(self.parentApp.filename, 'w') as f:
            json.dump(self.parentApp.data_dict, f)

        self.load_current_point_data()

    def while_waiting(self):
        self.scrollBoxRawData.entry_widget.buffer(
            [
                " ".join(["{:.2f}".format(i) for i in self.mag.get_values()])
            ]
        )
        self.scrollBoxRawData.display()

    def exit_application(self, optional=0):
        self.logger.debug('Exiting application code:{}'.format(optional))
        self.mag.stop()
        exit(0)


if __name__ == "__main__":
    npyscreen.wrapper(ManagerTUI().run())
