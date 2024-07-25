import gi, threading, time, webbrowser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class GUI:

    def __init__(self, dems):

        # Initialise the GUI object
        self.dems = dems
        self.builder = Gtk.Builder()
        self.selected_folder = None
        self.found_usb = False
        self.progress_text_value = ""

        self.add_xml()

        # Add the XML strings imported below
        self.builder.add_from_string(self.directorySelectorXml)
        self.builder.add_from_string(self.inputDetailsXml)
        self.builder.add_from_string(self.accessCodeXml)                    
        self.builder.add_from_string(self.uploadCompleteXml)
        self.builder.add_from_string(self.caseDetailsXml)
        self.builder.add_from_string(self.startWindowXml)
        self.builder.add_from_string(self.progressWindowXml)
        
        # Get references to the windows for calling .show() and .hide()
        self.folderWindow = self.builder.get_object("folder_window")
        self.inputWindow = self.builder.get_object("input_window")
        self.accessWindow = self.builder.get_object("access_code_window")
        self.completeWindow = self.builder.get_object("upload_complete_window")
        self.caseWindow = self.builder.get_object("case_window")
        self.startWindow = self.builder.get_object("start_window")
        self.progressWindow = self.builder.get_object("progress_window")

        # Allow closing each window to stop the program (apart from threads)
        self.folderWindow.connect("delete-event", Gtk.main_quit)
        self.inputWindow.connect("delete-event", Gtk.main_quit)
        self.accessWindow.connect("delete-event", Gtk.main_quit)
        self.completeWindow.connect("delete-event", Gtk.main_quit)
        self.caseWindow.connect("delete-event", Gtk.main_quit)
        self.startWindow.connect("delete-event", Gtk.main_quit)
        self.progressWindow.connect("delete-event", Gtk.main_quit)

        # Connect on_xyz_clicked to functions with the same name
        self.builder.connect_signals(self)

    def on_start_button_clicked(self, widget):

        self.startWindow.hide()
        self.inputWindow.show_all()

        print("Start button clicked")

    def on_choose_button_clicked(self, widget):

        # Create the folder chooser dialog
        dialog = Gtk.FileChooserDialog (
            title="Please choose a folder", 
            parent = self.folderWindow, 
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )

        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        # Show the folder chooser dialog
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Find the folder choice, display it on screen
            self.selected_folder = dialog.get_filename()
            self.selected_folder_label = self.builder.get_object("selected_folder_label")
            self.selected_folder_label.set_text("Selected folder: " + self.selected_folder)

        dialog.destroy()

    def on_confirm_button_clicked(self, widget):

        if self.selected_folder:
            # If a folder is selected, save the path, go to input screen
            print("Confirmed folder: " + self.selected_folder)
            self.dems.inputFolder = self.selected_folder
            self.dems.remount_readonly()
            self.folderWindow.hide()
            self.inputWindow.show_all()

        else:
            print("No folder selected!")
            self.msgbox_warning("No Folder Selected", "Please select a folder to continue.", self.folderWindow)
    
    def on_submit_button_clicked(self, widget):

        # Get the input from the text entry boxes
        name = self.builder.get_object("name_entry").get_text()
        wo = self.builder.get_object("wo_entry").get_text()
        email = self.builder.get_object("email_entry").get_text()

        # Check the formatting, give a warning message if wrong
        if name == "":
            print("Please enter a name")
            self.msgbox_warning("No Name Provided", "Please enter your name to continue", self.inputWindow)

        if not self.dems.check_string(wo, r'^z909996$'):
            print("Please enter a vald user ID")
            self.msgbox_warning("Invalid User ID", "Please enter your user ID to continue.", self.inputWindow)

        if not self.dems.check_string(email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'):
            print("Please enter a valid email address")
            self.msgbox_warning("Invalid Email Address", "Please enter a valid email address to continue", self.inputWindow)

        # If all correct, give an info message box reiterating stored values
        if self.dems.check_string(wo, r'^z909996$') and self.dems.check_string(email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$') and name != "":

            self.dems.name = name
            self.dems.wo = wo
            self.dems.email = email

            print("Name recorded :", name)
            print("User ID recorded :", wo)
            print("Email recorded :", email)

            # Go to case details window
            self.inputWindow.hide()
            self.caseWindow.show_all()

    def on_confirm_case_clicked(self, widget):

        # Check case details and what3words are correctly formatted
        case_no = self.builder.get_object("case_number_entry").get_text()
        what3words = self.builder.get_object("what3words_entry").get_text()

        # If not give a warning message
        if case_no == "":
            print("Please enter a case number")
            self.msgbox_warning("No Case Number", "Please enter a case number to continue", self.caseWindow)

        correct_w3w_format = self.dems.check_string(what3words, r'^[a-zA-Z]+\.[a-zA-Z]+\.[a-zA-Z]+$')
        
        if not correct_w3w_format:
            print("Please enter a valid what3words location.")
            self.msgbox_warning(
                "Invalid What3Words Location",
                "Please enter a valid What3Words location to continue.",
                self.caseWindow
            )

        # If all correct give an info box message confirming details
        if case_no != "" and correct_w3w_format:

            print("Case number recorded :", case_no)

            # Save details to dems object
            self.dems.case_no = case_no
            self.dems.what3words = what3words

            # Go to access code input window
            self.caseWindow.hide()

            # Start scanning (background progress)
            self.dems.get_timestamp()
            threading.Thread(target = self.dems.scan_folder, args = (self,)).start()
            
            # Show progress window and checkneeds to be renamed
            self.progressWindow.show_all()
            self.dems.gui_main_start()

    def on_confirm_access_clicked(self, widget):

        # Get the auth code from the entry box and finish dropbox authflow
        auth_code = self.builder.get_object("access_code_entry").get_text()
        self.dems.dropbox_auth_flow_finish(auth_code)

    def on_complete_clicked(self, widget):

        # End of GUI (from complete screen)
        self.progressWindowWindow.destroy()
        Gtk.main_quit()

    def msgbox_info(self, title, text, parent):

        # Take title and text and show an info box
        dialog = Gtk.MessageDialog(
            message_type = Gtk.MessageType.INFO,
            buttons = Gtk.ButtonsType.OK,
            text = title,
            parent = parent
        )

        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def msgbox_warning(self, title, text, parent):
               
        # Take title and text and shows a warning box
        dialog = Gtk.MessageDialog(
            message_type = Gtk.MessageType.WARNING,
            buttons = Gtk.ButtonsType.OK,
            text = title,
            parent = parent
        )

        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def msgbox_question(self, title, text, parent, yesFunc, noFunc):

        # Take title and text and shows a warning box
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text = title,
            parent = parent
        )

        dialog.format_secondary_text(text)
        response = dialog.run()

        if response == Gtk.ResponseType.YES:
            dialog.destroy()
            yesFunc()
        elif response == Gtk.ResponseType.NO:
            noFunc()
            dialog.destroy()

    def on_check_button_clicked(self, widget):

        # Get on sceen objects (start screen)
        devices_label = self.builder.get_object("devices_label")
        start_button = self.builder.get_object("start_button")
        check_button = self.builder.get_object("check_button")

        # First time go here, until USB detected
        if not self.found_usb:

            # Look for USB device
            self.dems.find_usb_devices()

            if len(self.dems.usb_drives) == 0:
                devices_label.set_text("No USB devices drives detected.")
                self.msgbox_warning("No USB Drive Found", "Please insert the USB drive and try again.", self.startWindow)
            else :
                # Save the usb path, change button to say lock drive
                self.usb_drive = self.dems.usb_drives[0]["mountpoint"]
                devices_label.set_text(f"USB drive detected : {self.usb_drive}")
                check_button.set_label("Lock Drive")
                self.found_usb = True

        # After USB drive has been found (clicking Lock Drive goes here)
        else:
            # Lock the drive, let the user now, unlock the start buttown
            self.dems.inputFolder = self.usb_drive
            successful = self.dems.remount_readonly()

            if successful:
                devices_label.set_text(f"USB Locked : {self.usb_drive}")
                self.msgbox_info("Device Locked", "The USB drive has mounted as read-only. Write protection enabled.", self.startWindow)
                start_button.set_property("sensitive", "True")

            else:
                self.msgbox_warning("Authentication Failed", "Root access is required to mount the USB in a read-only state.", self.startWindow)
            
    
    def on_next_button_clicked(self, widget):

        if self.dems.end_of_program:

            self.completeWindow.destroy()
            self.dems.httpd.shutdown()
            Gtk.main_quit()

        else:
            self.msgbox_question(

                "USB Contents", 
                "Do you want to upload the contents of the USB to Evidence-POC? (Will open to browser to login)",self.progressWindow,
                self.dropbox_yes,
                self.dropbox_no
            )

    def dropbox_no(self):

        # No state change (leaves results window open)
        pass

    def dropbox_yes(self):

        # Open the access code window and start auth flow from dropbox
        self.progressWindow.hide()

        # self.accessWindow.show_all()
        # self.dems.dropbox_auth_flow_start()

        self.dems.auth_in_progress = True

        threading.Thread(
            target = self.dems.dropbox_redirect_auth_flow_start
        ).start()

        while self.dems.auth_in_progress:
            for i in range(10):
                self.dems.gui.update_gui()
            time.sleep(0.1)

        self.msgbox_info(
            "Authorisation Complete",
            "Click OK to start the upload process.",
            None
        )        

        self.dems.main_finish()

    def progress_text(self, text, append = True):

        # Helper function to easily change progress window textView buffer

        textView = self.builder.get_object("output_text_view")
        buffer = textView.get_buffer()

        # Append to the end of the box by default (option to replace text)
        if append:
            self.progress_text_value += text
        else :
            self.progress_text_value = text

        buffer.set_text(self.progress_text_value)

        # Autoscroll to the end of the box

        scrollWindow = self.builder.get_object("scroll_window")
        adj = scrollWindow.get_vadjustment()
        adj.set_value( adj.get_upper() - adj.get_page_size() )

    def show_complete(self):

        # Show the upload complete window (Need to change to call .show() directly)
        self.completeWindow.show()
        
    def start(self):

        # Start of the GUI process
        self.startWindow.show_all()

        startGui = threading.Thread(
            target = self.start_gtk,
            args = (self,)
        )

        startGui.start()

    def update_gui(self):

        # Manual update of GUI (to prevent freezing)
        while Gtk.events_pending():
            Gtk.main_iteration()


    def start_gtk(self, threadArgs):

        # Can be called from threading.Thread directly as well
        
        Gtk.main()

    def on_help_button_clicked(self, widget):

        entry = self.builder.get_object("what3words_entry")
        text = entry.get_text()

        correct_w3w_format = self.dems.check_string(text, r'^[a-zA-Z]+\.[a-zA-Z]+\.[a-zA-Z]+$')

        if not correct_w3w_format:

            self.msgbox_warning(
                "What3Words Location Format",
                "The What3Words location must be in the format [word].[word].[word]",
                self.caseWindow
            )

        else : 
            result = self.dems.w3w.convert_to_coordinates(text)

            print("Result from What3Words :")
            print(result)

            if "error" in result:

                self.msgbox_warning(
                "Invalid What3Words Location",
                "The What3Words location you have entered does not match a know grid spot with the service.",
                self.caseWindow
                )

            else:

                if "code" in result:
                    self.msgbox_warning(
                        "Quota Exceeded",
                        "The What3Words API quota has been exceeded",
                        self.caseWindow
                    )

                else:

                    nearest = result.get("nearestPlace")
                    self.w3w_url = result.get("map")
                    self.msgbox_question(
                        "What3Words Location",
                        f"The What3Words location : {text} resolves to {nearest}. Would you like to view this on the map?",
                        self.caseWindow,
                        self.w3w_yes,
                        self.w3w_no
                    )

                    label = self.builder.get_object("what3words_label")
                    label.set_text(f"The grid at {text} is near {nearest}.")

        
    def w3w_yes(self) :
    
      webbrowser.open(self.w3w_url)


    def w3w_no(self):
    
      pass

        
    def on_what3words_entry_changed(self, widget):

        return
    
        # No longer in use

        # text = widget.get_text()
        # result = self.dems.w3w.convert_to_coordinates(text)
        # label = self.builder.get_object("what3words_label")

        # if not "error" in result:
        #     nearest = result.get("nearestPlace")
        #     label.set_text(nearest)
        # else :
        #     label.set_text("Please enter a valid What3Words address.")

    def add_xml(self):

        # Add the GUI xml strings 
        self.progressWindowXml = '''
            <?xml version="1.0" encoding="UTF-8"?>
            <!-- Generated with glade 3.40.0 -->
            <interface>
              <requires lib="gtk+" version="3.0"/>
              <object class="GtkWindow" id="progress_window">
                <property name="can-focus">False</property>
                <property name="title">Progress Window</property>
                <property name="default-width">400</property>
                <property name="default-height">400</property>
                <child>
                  <object class="GtkBox">
                    <property name="can-focus">False</property>
                    <property name="orientation">vertical</property>
                    <property name="spacing">14</property>
                    <child>
                      <object class="GtkBox">
                        <property name="can-focus">False</property>
                        <property name="halign">center</property>
                        <property name="spacing">10</property>
                        <child>
                          <object class="GtkLabel" id="progress_label">
                            <property name="can-focus">False</property>
                            <property name="label">Scanning in progress, please wait...</property>
                          </object>
                          <packing>
                            <property name="expand">False</property>
                            <property name="fill">False</property>
                            <property name="padding">10</property>
                            <property name="position">0</property>
                          </packing>
                        </child>
                        <child>
                          <object class="GtkSpinner" id="progress_spinner">
                            <property name="can-focus">False</property>
                            <property name="active">True</property>
                          </object>
                          <packing>
                            <property name="expand">False</property>
                            <property name="fill">False</property>
                            <property name="padding">10</property>
                            <property name="position">1</property>
                          </packing>
                        </child>
                      </object>
                      <packing>
                        <property name="expand">False</property>
                        <property name="fill">True</property>
                        <property name="padding">10</property>
                        <property name="position">0</property>
                      </packing>
                    </child>
                    <child>
                      <object class="GtkScrolledWindow" id="scroll_window">
                        <property name="can-focus">False</property>
                        <property name="hexpand">True</property>
                        <property name="vexpand">True</property>
                        <child>
                          <object class="GtkTextView" id="output_text_view">
                            <property name="can-focus">False</property>
                            <property name="editable">False</property>
                            <property name="wrap-mode">word</property>
                            <property name="left-margin">20</property>
                            <property name="right-margin">20</property>
                          </object>
                        </child>
                      </object>
                      <packing>
                        <property name="expand">True</property>
                        <property name="fill">True</property>
                        <property name="padding">10</property>
                        <property name="position">1</property>
                      </packing>
                    </child>
                    <child>
                      <object class="GtkBox">
                        <property name="visible">True</property>
                        <property name="can-focus">False</property>
                        <property name="spacing">10</property>
                        <child>
                          <placeholder/>
                        </child>
                        <child>
                          <object class="GtkButton" id="next_button">
                            <property name="label" translatable="yes">Next</property>
                            <property name="visible">True</property>
                            <property name="sensitive">False</property>
                            <property name="can-focus">True</property>
                            <property name="receives-default">True</property>
                            <signal name="clicked" handler="on_next_button_clicked" swapped="no"/>
                          </object>
                          <packing>
                            <property name="expand">True</property>
                            <property name="fill">True</property>
                            <property name="position">1</property>
                          </packing>
                        </child>
                        <child>
                          <placeholder/>
                        </child>
                      </object>
                      <packing>
                        <property name="expand">False</property>
                        <property name="fill">True</property>
                        <property name="padding">8</property>
                        <property name="position">2</property>
                      </packing>
                    </child>
                  </object>
                </child>
              </object>
            </interface>

'''

        self.startWindowXml = ''' 

<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkWindow" id="start_window">
    <property name="title">Start Window</property>
    <property name="default_width">400</property>
    <property name="default_height">200</property>
    <child>
      <object class="GtkBox">
        <property name="orientation">vertical</property>
        <property name="spacing">10</property>
        <property name="margin">20</property>
        <child>
          <object class="GtkLabel" id="instruction_label">
            <property name="label">Please enter a USB drive</property>
          </object>
          <packing>
            <property name="padding">10</property>
          </packing>
        </child>
        <child>
          <object class="GtkLabel" id="devices_label">
            <property name="label"></property>
          </object>
          <packing>
            <property name="padding">10</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox">
            <property name="orientation">horizontal</property>
            <property name="halign">center</property>
            <child>
              <object class="GtkButton" id="check_button">
                <property name="label">Check USB</property>
                <property name="sensitive">True</property> <!-- Greyed out -->

                <property name="width_request">150</property>
                <signal name="clicked" handler="on_check_button_clicked"/>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">False</property>
              </packing>
            </child>
            <child>
              <object class="GtkSeparator" id="separator">
                <property name="orientation">vertical</property>
                <property name="margin_left">10</property> <!-- Adjust spacing here -->
                <property name="margin_right">10</property> <!-- Adjust spacing here -->
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">False</property>
              </packing>
            </child>
            <child>
              <object class="GtkButton" id="start_button">
                <property name="label">Start</property>
                <property name="sensitive">False</property> <!-- Greyed out -->
                <property name="width_request">150</property>
                <signal name="clicked" handler="on_start_button_clicked"/>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">False</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="padding">10</property>
            <property name="expand">False</property>
            <property name="fill">False</property>
          </packing>
        </child>
      </object>
    </child>
  </object>
</interface>



        '''

        self.caseDetailsXml = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <requires lib="gtk+" version="3.0"/>
  <object class="GtkWindow" id="case_window">
    <property name="title">Case Details</property>
    <property name="default_width">400</property>
    <property name="default_height">200</property>
    <child>
      <object class="GtkBox">
        <property name="orientation">vertical</property>
        <property name="spacing">10</property>
        <property name="margin">20</property>
        <child>
          <object class="GtkLabel">
            <property name="label">Please enter the case details, and then click confirm.</property>
            <property name="xalign">0</property>
            <property name="margin-bottom">10</property>
          </object>
        </child>
        <child>
          <object class="GtkGrid">
            <property name="column-spacing">10</property>
            <property name="row-spacing">10</property>
            <property name="margin-bottom">10</property>
            <child>
              <object class="GtkLabel">
                <property name="label">Case No.</property>
                <property name="xalign">0</property>
              </object>
              <packing>
                <property name="left-attach">0</property>
                <property name="top-attach">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkAlignment">
                <property name="left-padding">10</property>
                <property name="right-padding">10</property>
                <property name="hexpand">True</property>
                <child>
                  <object class="GtkEntry" id="case_number_entry"/>
                </child>
              </object>
              <packing>
                <property name="left-attach">1</property>
                <property name="top-attach">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkLabel">
                <property name="label">What3Words</property>
                <property name="xalign">0</property>
              </object>
              <packing>
                <property name="left-attach">0</property>
                <property name="top-attach">1</property>
              </packing>
            </child>
            <child>
              <object class="GtkAlignment">
                <property name="left-padding">10</property>
                <property name="right-padding">10</property>
                <property name="hexpand">True</property>
                <child>
                  <object class="GtkEntry" id="what3words_entry">
                    <signal name="changed" handler="on_what3words_entry_changed" swapped="no"/>
                  </object>
                </child>
              </object>
              <packing>
                <property name="left-attach">1</property>
                <property name="top-attach">1</property>
              </packing>
            </child>
            <!-- New Label underneath What3Words Entry -->
            <child>
              <object class="GtkLabel" id="what3words_label">
                <property name="label">Please enter a valid What3Words address.</property>
                <property name="visible">True</property>
              </object>
              <packing>
                <property name="left-attach">0</property>
                <property name="top-attach">2</property>
                <property name="width">2</property>
              </packing>
            </child>
            <!-- New Button with "?" Label next to What3Words Entry -->
            <child>
              <object class="GtkButton" id="help_button">
                <property name="label">?</property>
                <property name="visible">True</property>
                <signal name="clicked" handler="on_help_button_clicked" swapped="no"/>
              </object>
              <packing>
                <property name="left-attach">2</property>
                <property name="top-attach">1</property>
              </packing>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkButton" id="confirm_case_button">
            <property name="label">Confirm</property>
            <property name="halign">center</property>
            <property name="width-request">100</property>
            <property name="height-request">40</property>
            <signal name="clicked" handler="on_confirm_case_clicked" swapped="no"/>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""     

        self.directorySelectorXml = '''

            <?xml version="1.0" encoding="UTF-8"?>
            <!-- Generated with glade 3.40.0 -->
            <interface>
            <requires lib="gtk+" version="3.20"/>
            <object class="GtkWindow" id="folder_window">
                <property name="can-focus">False</property>
                <property name="title">Directory Selector</property>
                <child>
                <object class="GtkFixed" id="fixed_container">
                    <property name="width-request">435</property>
                    <property name="height-request">200</property>
                    <property name="can-focus">False</property>
                    <child>
                    <object class="GtkLabel" id="prompt_label">
                        <property name="can-focus">False</property>
                        <property name="label">Please select the USB you want to scan</property>
                    </object>
                    <packing>
                        <property name="x">25</property>
                        <property name="y">25</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkLabel" id="selected_folder_label">
                        <property name="width-request">125</property>
                        <property name="height-request">20</property>
                        <property name="can-focus">False</property>
                        <property name="label">No folder selected</property>
                        <property name="xalign">0</property>
                    </object>
                    <packing>
                        <property name="x">25</property>
                        <property name="y">75</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkButton" id="choose_button">
                        <property name="label">Choose Folder</property>
                        <property name="width-request">150</property>
                        <property name="height-request">34</property>
                        <property name="can-focus">True</property>
                        <property name="receives-default">False</property>
                        <signal name="clicked" handler="on_choose_button_clicked" swapped="no"/>
                    </object>
                    <packing>
                        <property name="x">39</property>
                        <property name="y">140</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkButton" id="confirm_button">
                        <property name="label">Confirm</property>
                        <property name="width-request">150</property>
                        <property name="height-request">34</property>
                        <property name="can-focus">True</property>
                        <property name="receives-default">False</property>
                        <signal name="clicked" handler="on_confirm_button_clicked" swapped="no"/>
                    </object>
                    <packing>
                        <property name="x">246</property>
                        <property name="y">140</property>
                    </packing>
                    </child>
                </object>
                </child>
            </object>
            </interface>

        '''

        self.uploadCompleteXml = '''

            <?xml version="1.0" encoding="UTF-8"?>
            <interface>
            <requires lib="gtk+" version="3.20"/>
            <object class="GtkWindow" id="upload_complete_window">
                <property name="title">Upload Complete</property>
                <property name="default_width">400</property>
                <property name="default_height">200</property>
                <child>
                <object class="GtkFixed" id="fixed_container">
                    <property name="visible">True</property>
                    <child>
                    <object class="GtkLabel" id="upload_complete_label">
                        <property name="label">Upload complete</property>
                        <property name="halign">center</property>
                        <property name="visible">True</property>
                        <property name="can_focus">False</property>
                        <property name="hexpand">True</property>
                    </object>
                    <packing>
                        <property name="y">20</property>
                        <property name="x">20</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkLabel" id="close_info_label">
                        <property name="label">You may now close this window</property>
                        <property name="halign">center</property>
                        <property name="visible">True</property>
                        <property name="can_focus">False</property>
                        <property name="hexpand">True</property>
                    </object>
                    <packing>
                        <property name="y">60</property>
                        <property name="x">20</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkButton" id="close_button">
                        <property name="label">Close</property>
                        <property name="width_request">100</property>
                        <property name="height_request">30</property>
                        <property name="visible">True</property>
                        <property name="can_focus">True</property>
                        <property name="hexpand">False</property>
                        <property name="halign">center</property>
                        <signal name="clicked" handler="on_complete_clicked" swapped="no"/>
                    </object>
                    <packing>
                        <property name="y">120</property>
                        <property name="x">150</property>
                    </packing>
                    </child>
                </object>
                </child>
            </object>
            </interface>

        '''

        self.inputDetailsXml = '''

            <?xml version="1.0" encoding="UTF-8"?>
            <!-- Generated with glade 3.40.0 -->
            <interface>
            <requires lib="gtk+" version="3.24"/>
            <object class="GtkWindow" id="input_window">
                <property name="can-focus">False</property>
                <property name="title">User Information</property>
                <property name="default-width">400</property>
                <property name="default-height">200</property>
                <child>
                <!-- n-columns=3 n-rows=4 -->
                <object class="GtkGrid" id="grid">
                    <property name="can-focus">False</property>
                    <property name="row-spacing">10</property>
                    <property name="column-spacing">10</property>
                    <property name="margin-top">20</property>
                    <property name="margin-start">20</property>
                    <property name="margin-end">20</property>
                    <child>
                    <object class="GtkLabel" id="name_label">
                        <property name="can-focus">False</property>
                        <property name="label">Name:</property>
                    </object>
                    <packing>
                        <property name="left-attach">0</property>
                        <property name="top-attach">0</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkEntry" id="name_entry">
                        <property name="can-focus">True</property>
                        <property name="hexpand">True</property>
                    </object>
                    <packing>
                        <property name="left-attach">1</property>
                        <property name="top-attach">0</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkLabel" id="wo_label">
                        <property name="can-focus">False</property>
                        <property name="label">User ID:</property>
                    </object>
                    <packing>
                        <property name="left-attach">0</property>
                        <property name="top-attach">1</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkEntry" id="wo_entry">
                        <property name="can-focus">True</property>
                        <property name="hexpand">True</property>
                    </object>
                    <packing>
                        <property name="left-attach">1</property>
                        <property name="top-attach">1</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkLabel" id="email_label">
                        <property name="can-focus">False</property>
                        <property name="label">Email:</property>
                    </object>
                    <packing>
                        <property name="left-attach">0</property>
                        <property name="top-attach">2</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkEntry" id="email_entry">
                        <property name="can-focus">True</property>
                        <property name="hexpand">True</property>
                    </object>
                    <packing>
                        <property name="left-attach">1</property>
                        <property name="top-attach">2</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkButton" id="submit_button">
                        <property name="label">Submit</property>
                        <property name="can-focus">True</property>
                        <property name="receives-default">False</property>
                        <property name="halign">center</property>
                        <signal name="clicked" handler="on_submit_button_clicked" swapped="no"/>
                    </object>
                    <packing>
                        <property name="left-attach">0</property>
                        <property name="top-attach">3</property>
                        <property name="width">2</property>
                    </packing>
                    </child>
                    <child>
                    <placeholder/>
                    </child>
                    <child>
                    <placeholder/>
                    </child>
                    <child>
                    <placeholder/>
                    </child>
                    <child>
                    <placeholder/>
                    </child>
                </object>
                </child>
            </object>
            </interface>

        '''

        self.accessCodeXml = '''

            <?xml version="1.0" encoding="UTF-8"?>
            <!-- Generated with glade 3.40.0 -->
            <interface>
            <requires lib="gtk+" version="3.20"/>
            <object class="GtkWindow" id="access_code_window">
                <property name="can-focus">False</property>
                <property name="title">Access Code Input</property>
                <property name="default-width">400</property>
                <property name="default-height">200</property>
                <child>
                <object class="GtkBox" id="vbox">
                    <property name="can-focus">False</property>
                    <property name="margin-start">20</property>
                    <property name="margin-end">20</property>
                    <property name="margin-top">20</property>
                    <property name="margin-bottom">20</property>
                    <property name="orientation">vertical</property>
                    <property name="spacing">20</property>
                    <child>
                    <object class="GtkLabel" id="prompt_label">
                        <property name="can-focus">False</property>
                        <property name="label">Paste your access code from Evidence-POC here and click confirm</property>
                    </object>
                    <packing>
                        <property name="expand">False</property>
                        <property name="fill">True</property>
                        <property name="position">0</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkEntry" id="access_code_entry">
                        <property name="can-focus">True</property>
                        <property name="width-chars">40</property>
                    </object>
                    <packing>
                        <property name="expand">False</property>
                        <property name="fill">True</property>
                        <property name="position">1</property>
                    </packing>
                    </child>
                    <child>
                    <object class="GtkButton" id="confirm_code_button">
                        <property name="label">Confirm</property>
                        <property name="can-focus">True</property>
                        <property name="receives-default">False</property>
                        <signal name="clicked" handler="on_confirm_access_clicked" swapped="no"/>
                    </object>
                    <packing>
                        <property name="expand">True</property>
                        <property name="fill">True</property>
                        <property name="position">2</property>
                    </packing>
                    </child>
                </object>
                </child>
            </object>
            </interface>


        '''

    