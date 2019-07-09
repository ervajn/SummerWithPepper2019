import time
import os
import threading
from Modules.service import ServiceBaseClass
import datetime
from Applications.Vasttrafik import Vasttrafik


class VasttrafikService(ServiceBaseClass):
    """
    A module to handle interaction between the robot and the vasttrafik API.
    """

    def __init__(self, app, name, pepper_ip):
        """
        Initialisation of qi framework and event detection.
        """
        # Folder name on Pepper
        folder_name = "vasttrafik"
        # Superclass init call
        super(VasttrafikService, self).__init__(app, name, pepper_ip, folder_name)
        # Create a Vasttrafik object for handling API calls
        self.vt = Vasttrafik(self.local_html_path)
        # Thread initialization
        self.t = None

    def initiate_dialog(self):
        self.tablet.hideWebview()

        self.topic = self.dialog.loadTopic("/home/nao/VasttrafikGreetingMod_enu.top")
        self.dialog.activateTopic(self.topic)
        self.dialog.subscribe(self.name)
        self.memory.insertData("trip_time", 0)
        self.display_on_tablet('vasttrafik.html', False)
        self.tts.say("Do you want to see the next rides or plan a trip")

        self.rides_subscriber = self.memory.subscriber("next_ride")
        self.next_ride_id = self.rides_subscriber.signal.connect(self.next_ride)
        self.trip_subscriber = self.memory.subscriber("trip")
        self.trip_id = self.trip_subscriber.signal.connect(self.trip)

        self.new_view_subscriber = self.memory.subscriber("new_view")
        self.new_view_id = self.new_view_subscriber.signal.connect(self.display_on_tablet)

    def next_ride(self, *_args):
        """
        Callback for when next_ride is set
        """
        print "Next ride callback started"

        self.tablet.hideWebview()
        self.dialog.deactivateTopic(self.topic)
        self.dialog.unloadTopic(self.topic)
        self.dialog.unsubscribe(self.name)

        file_name = 'next_ride'
        file_ending = '.htm'
        full_file_name = file_name + file_ending

        self.hide_tablet = False
        self.t = threading.Thread(target=self.display_on_tablet, args=(full_file_name, True))
        self.t.start()
        time.sleep(5)

        self.module_finished = True

    def trip(self, *_args):
        """
        Callback for when trip is set
        """
        print "Trip callback started"
        self.tts.say("Fetching trip data")

        goal = self.memory.getData("arr_stop")
        dep = self.memory.getData("dep_stop")
        time_delta = self.memory.getData("trip_time")
        print 'time is: ' + str(time_delta)

        trip_time = datetime.datetime.now() + datetime.timedelta(minutes=int(time_delta))
        trip_time = trip_time.strftime("%H%M")
        print "From: %s" % dep
        print "To: %s" % goal
        self.tablet.hideWebview()

        file_name = 'trip'
        file_ending = '.htm'
        full_file_name = file_name + file_ending
        full_path = os.path.join(self.local_html_path, full_file_name)

        print "Connecting to Vasttrafik and getting trip info"
        try:
            self.vt.calculate_trip(start_station=dep, end_station=goal, trip_time=trip_time)

            print "Download complete"
            self.transfer_to_pepper(full_path)

            self.display_on_tablet(full_file_name, False)
            time.sleep(10)
            self.module_finished = True
            self.dialog.deactivateTopic(self.topic)
            self.dialog.unloadTopic(self.topic)
            self.dialog.unsubscribe(self.name)
        except KeyError:
            error_string = 'I am sorry, something went wrong.' \
                           ' I couldn\'t plan a trip from %s to %s. Let\'s try again' % (dep, goal)
            self.tts.say(error_string)
            self.display_on_tablet('vasttrafik.html', False)
            self.memory.raiseEvent('trip_click', 1)

    def display_on_tablet(self, full_file_name, update=False):
        """
        Display file on Pepper's tablet
        :param full_file_name: file name including file ending
        :param update: if view should be updated (only used with next rides)
        """
        self.tablet.enableWifi()
        ip = self.tablet.robotIp()
        remote_path = 'http://%s/apps/%s/%s' % (ip, self.folder_name, full_file_name)
        if update:
            while True:
                full_path = os.path.join(self.local_html_path, full_file_name)

                file_name = full_file_name.split('.')[0]

                print "Connecting to Vasttrafik and getting next rides"
                self.vt.create_departure_html(file_name)
                print "Download complete"

                self.transfer_to_pepper(full_path)
                self.tablet.showWebview(remote_path)

                time.sleep(5)  # Update view with new data every 3 seconds
                if self.hide_tablet:
                    print "Killing thread and hiding tablet"
                    self.tablet.hideWebview()
                    break
        else:
            self.tablet.showWebview(remote_path)

    def shutoff(self, *_args):
        """
        Shutoff and unsubscribe to events. Trigger ModuleFinished event.
        """
        try:
            self.dialog.deactivateTopic(self.topic)
            self.dialog.unloadTopic(self.topic)
            self.dialog.unsubscribe(self.name)
            print "Stopped dialog"
        except RuntimeError:
            pass
        except AttributeError:
            pass
        try:
            self.hide_tablet = True
            if self.t is not None:
                print "Main waiting for thread to die"
                self.t.join()
            self.tablet.hideWebview()
            print "Tabletview stopped"
        except:
            pass
        self.module_finished = False

    def run(self):
        self.initiate_dialog()
        while not self.module_finished:
            time.sleep(1)
        self.shutoff()
