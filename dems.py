#! /usr/bin/env python3 

import subprocess, os, hashlib, re, dropbox, webbrowser, keyring, time, threading, pathlib, http.server, urllib.parse, what3words
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from gui import GUI

class DEMS:

    def __init__(self):

        print("DEMS initialised")

        # Initiaise the DEMS instance                
        self.gui = GUI(self)
        self.compression = True
        self.tempPath = "/tmp/"
        self.homeFolder = os.path.expanduser("~")
        self.projectRoot = self.homeFolder +"/DEMS"
        self.scanFinished = False
        self.progress_text_value = ""
        self.end_of_program = False

        file = open(f"{self.projectRoot}/w3w_api_key.txt", "r")
        lines = file.readlines()
        w3w_api_key = lines[0].strip()
        self.w3w = what3words.Geocoder(w3w_api_key)

    def get_timestamp(self):

        # Take a timestamp from the system
        now = datetime.now()
        self.timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    def scan_folder(self, threadArgs):

        # Call a subprocess that starts the scan
        scanScript = f"{self.projectRoot}/scan.sh"
        subprocess.run([scanScript, self.inputFolder])

    def check_scan_progress(self):

        # Ensure the log has cleared (sometimes thread overtakes)
        time.sleep(5)

        finishedScan = False
        while not finishedScan:

            # Open the log file
            file = open("/tmp/temp_log.txt", "r")
            lines = file.readlines()
            file.close()

            # Look for the word "End" to know when finished
            for line in lines:
                line = line.strip() # 
                pos = line.find("End")
                if pos != -1:
                    finishedScan = True
                    self.scanFinished = True
                    self.gui.builder.get_object("next_button").set_property("sensitive", "True")

            time.sleep(1)

    def after_scan(self):

        print("Scan finished")

        # Set the scan summary temp path
        self.summaryPath = self.tempPath + f"Full Scan Report {self.timestamp}"

        # Rename the temp log path with the timestamp
        os.rename("/tmp/temp_log.txt", self.summaryPath)
        print(f"Scan log written to : {self.summaryPath}")

        # Look at the log and update the summary to the window
        self.inspect_results()
        summaryString = "\n" + "".join(self.scanSummary)

        summaryString += "\nInfected Files : \n"

        if len(self.infected) == 0:
            summaryString += "No malware detected"
        else :
            for mal in self.infected:
                summaryString += "Filename :\n"
                summaryString += mal[0] + "\n"
                summaryString += "Malware Type:\n"
                summaryString += mal[1] + "\n\n"

        output = self.gui.builder.get_object("output_text_view")
        buffer = output.get_buffer()
        buffer.set_text(summaryString)

        self.gui.progressWindow.set_title("Scan Results")
        label = self.gui.builder.get_object("progress_label")
        label.set_text("Scan complete.")

        spinner = self.gui.builder.get_object("progress_spinner")
        spinner.set_visible(False)
        spinner.stop()

    def inspect_results(self):

        # Open the scan log from /tmp and read it in
        file = open(self.summaryPath, "r")
        lines = file.readlines()
        file.close()

        # Read through the file and isolate malware name / reason
        infected = []
        for line in lines:
            line = line.strip()
            pos = line.find("FOUND")
            if pos != -1:
                infectedLine = line[:pos - 1]
                pos2 = infectedLine.find(":")
                path = infectedLine[:pos2]
                reason = infectedLine[pos2 + 2:]
                infected.append([path, reason])

        # Find the scan summary from clamcan and "borrow" it :)        
        for i in range(len(lines)):
            if lines[i].find("SCAN SUMMARY") != -1:
                self.scanSummary = lines[i + 1:]

        # Save the infected files / reasons for report and print them
        self.infected = infected
        print("\nInfected files below \n")
        print(infected, "\n")

    def zip_folder(self):

        self.uploadState = "zipping"

        # Open a new zip file with timestamp as the name
        self.zipPath = self.tempPath + f"{self.timestamp}.zip"

        # Options for zipping compressed or not (default on)
        if self.compression:
            zf = ZipFile(self.zipPath, "w", ZIP_DEFLATED)
        else:
            zf = ZipFile(self.zipPath, "w")


        # Remove the /{username}]/media prefix from the final zip
        username = self.homeFolder.replace("/home/", "")
        print("Username :", username)
        stringToRemove = f"/media/{username}/"
        folderToZip = self.inputFolder.replace(stringToRemove, "")
        
        # For each folder and file in target folder
        for dirname, subdirs, files in os.walk(self.inputFolder):
            for filename in files:
                malware = False
                # For each malware name recorded earlier
                for name, reason in self.infected:
                    if filename in name:
                        malware = True
                        print("Malware", filename)
                # If it is malware, prefix the name first
                if malware:
                    malware_filename = "MALWARE >>> " + filename
                    print("New filename:", filename)
                # AAnd either way zip it the the zip
                print("Zipping :", filename)
                self.progress_text_value +=f"Zipping : {filename}\n"

                # Need to remove  /home/user
                usbfile = os.path.join(dirname, filename)
                arcfile = usbfile.replace(self.inputFolder, "")
                if malware:
                    print("If malware conditional triggered")
                    arcfile = arcfile.replace(filename, malware_filename)
                    print("Filename : ", filename)
                    print("malwre_filename", malware_filename)
                    print("New arcfile: ", arcfile)
                print("Zipping original file :", usbfile)
                print("Into archive at:", arcfile)
                zf.write(usbfile, arcname = arcfile)

        # Close the zip file when finished looping through files
        zf.close()
        print("Zip closed")
        self.progress_text_value += f"Zip closed\n"
        print(f"Contents zipped to : {self.zipPath}")
        self.progress_text_value += f"Contents zipped to : {self.zipPath}\n\n"


    def get_checksum(self):

        self.uploadState = "hashing"

        # Open the zip in read binary mode
        with open(self.zipPath, "rb") as file:
            # Read the contents
            contents = file.read()
            # Create md5 hash object
            md5 = hashlib.md5()
            # Run the binary through the hash function
            md5.update(contents)
            # Get hexadecimal checksum
            self.checksum = md5.hexdigest()
            print("MD5 hash :", self.checksum)
            self.progress_text_value += f"MD5 hash : {self.checksum}\n\n"
            

    def check_string(self, text, pattern):

        # Check general regular expression by passing expression with text
        match = re.search(pattern, text)

        # Return true/false based on object / None
        if match:
            return True
        else:
            return False
        
    def compile_report(self):
        
        self.uploadState = "compiling"

        # Writes lines to a text file based on input and scan
        print("Compiling report...")
        self.progress_text_value += "Compiling report...\n"
        self.reportPath = self.tempPath + f"Upload Report {self.timestamp}.txt"
        file = open(self.reportPath, "w")

        file.write("----------- USER DETAILS -----------\n")
        file.write("\n")
        file.write(f"Name : {self.name}\n")
        file.write(f"User ID : {self.wo}\n")
        file.write(f"Email : {self.email}\n")
        file.write(f"Date / Time : {self.timestamp}\n")
        file.write("\n")
        file.write("----------- CASE DETAILS -----------\n")
        file.write("\n")
        file.write(f"Case Number : {self.case_no}\n")
        file.write(f"What3Words Location : {self.what3words}\n")
        file.write("\n")
        file.write("----------- SCAN SUMMARY -----------\n")
        file.write("\n")

        for line in self.scanSummary: 
            file.write(line)

        file.write("\n")
        file.write("---------- INFECTED FILES ----------\n")

        if len(self.infected) > 0 :
            for mal in self.infected:
                file.write("\n")
                file.write("File :\n")
                file.write(mal[0])
                file.write("\n") 
                file.write("Malware Type :\n")
                file.write(mal[1])
                file.write("\n")
        else :
            file.write("\n")
            file.write("No malware detected.\n")

        file.write("\n")
        file.write("------------- ZIP NAME -------------\n")
        file.write("\n")
        file.write(f"{self.timestamp}/USB Contents.zip")
        file.write("\n")
        file.write("\n")
        file.write("----------- MD5 Checksum -----------\n")
        file.write("\n")
        file.write(self.checksum)

        file.close()
        print(f"Report written to {self.reportPath}")
        self.progress_text_value += f"Report written to {self.reportPath}\n\n"

    def get_app_key_secret(self):

        try:
            # Decrypts the app key and secret from local storags
            self.app_key = keyring.get_password("dropbox", "app_key")
            self.app_secret = keyring.get_password("dropbox", "app_secret")
        except:
            self.gui.msgbox_warning("Credentials Not Found", "You need to run save_keyring.py to save the app key and secret locally.", parent = None)

    def dropbox_redirect_auth_flow_start(self):

        self.redirect_auth_flow = dropbox.DropboxOAuth2Flow(
            consumer_key = self.app_key,
            consumer_secret = self.app_secret,
            session = {},
            csrf_token_session_key = "dropbox-auth-csrf-token",
            redirect_uri = "http://localhost:8080/oauth2/callback"
        )

        authorize_url = self.redirect_auth_flow.start()
        webbrowser.open(authorize_url)
        server_address = ("", 8080)
        self.httpd = http.server.HTTPServer(server_address, OAuthHandler)
        self.httpd.serve_forever()
        
    def dropbox_auth_flow_start(self):

        # Start the dropbox auth flow
        self.auth_flow = DropboxOAuth2FlowNoRedirect(self.app_key, self.app_secret)
        # Open the browser to dropbox
        authorize_url = self.auth_flow.start()
        webbrowser.open(authorize_url)


    def dropbox_auth_flow_finish(self, gui_auth_code):

        # Retries if auth fails
        try:
            # Finish the auth flow (GUI mode - auth code passed in)
            oauth_result = self.auth_flow.finish(gui_auth_code)
            self.access_token = oauth_result.access_token

        except:
            self.gui.builder.get_object("access_code_entry").set_text("")
            self.gui.msgbox_warning(
                "Authentication Failed",
                "The authentication has failed. Any access code already generated will now be revoked. Please authenticate through Evidence-POC and paste the full access code in the entry box",
                self.gui.accessWindow
            )
            self.dropbox_auth_flow_start()

        else:
            self.gui.accessWindow.hide()
            self.main_finish()


    def dropbox_upload(self):

        self.uploadState = "uploading"

        # Create the dropbox object (with 10min timeout)    
        dbx = dropbox.Dropbox(self.access_token, timeout=600)

        # Open the zip file (read, binary) and uploads
        print("Uploading zip file...")
        self.progress_text_value += f"Uploading zip file...\n"
        with open(self.zipPath, "rb") as f:
            dbx.files_upload(f.read(), f"/Your Evidence Uploads/{self.timestamp}/USB Contents.zip")
        print("Done.\n")
        self.progress_text_value += "Done\n\n"

        # Open the scan summary file (read, binary) and uploads
        print("Uploading scan summary... ")
        self.progress_text_value += "Uplading scan summary...\n"
        with open(self.summaryPath, "rb") as f:
            dbx.files_upload(f.read(), f"/Your Evidence Uploads/{self.timestamp}/Full Scan Details.txt")
        print("Done.\n")
        self.progress_text_value += "Done\n\n"
        
        # Open the report file (read, binary) and uploads
        print("Uploading report...")
        self.progress_text_value += "Uploading report...\n"
        with open(self.reportPath, "rb") as f:
            dbx.files_upload(f.read(), f"/Your Evidence Uploads/{self.timestamp}/Upload Report.txt")
        print("Done.\n")
        self.progress_text_value += "Done\n\n"
        
        print("Uploads complete.")
        self.progress_text_value += "Uploads complete."

        self.progressLabel.set_text("Uploads complete.")
        self.progressSpinner.stop()
        self.progressSpinner.set_visible(False)

    def gui_interface(self):

        # Starts the GUI route (continues after details input)
        self.get_app_key_secret()
        self.gui.start()

    def gui_main_start(self):

        # Scan already in progress now, check if finished
        self.gui.progressWindow.show_all()

        threading.Thread(target = self.check_scan_progress).start()

        while not self.scanFinished:
            for i in range(10):
                self.gui.update_gui()
            time.sleep(0.1)

        self.after_scan()

    def update_progress_window(self):

        if self.uploadState == "zipping":
            self.gui.progressWindow.set_title("Zipping Directory")
            self.progressLabel.set_text("Zipping directory...")
            self.progressSpinner.start()

        elif self.uploadState == "hashing":
            self.gui.progressWindow.set_title("Hashing Directory")
            self.progressLabel.set_text("Hashing the directory...")

        elif self.uploadState == "compiling":
            self.gui.progressWindow.set_title("Compiling Report")
            self.progressLabel.set_text("Compiling report...")

        elif self.uploadState == "uploading":
            self.gui.progressWindow.set_title("Uploading Directory")
            self.progressLabel.set_text("Uploading to Evidence-POC...")

        self.gui.progress_text(self.progress_text_value, False)
    
    def upload_tasks(self):

        self.zip_folder()
        self.get_checksum()
        self.compile_report()
        self.dropbox_upload()

        time.sleep(3)

        self.uploading = False


    def main_finish(self):

        self.gui.progressWindow.set_title("Upload Process")
        progress_textView = self.gui.builder.get_object("output_text_view")
        progress_textView.get_buffer().set_text("")

        self.progressLabel = self.gui.builder.get_object("progress_label")
        self.progressSpinner = self.gui.builder.get_object("progress_spinner")
        self.progressButton = self.gui.builder.get_object("next_button")

        self.progressButton.set_label("Close")
        self.progressButton.set_sensitive(False)

        self.gui.progressWindow.show_all()

        self.uploading = True

        threading.Thread(target = self.upload_tasks).start()

        while self.uploading:
            for i in range(10):
                self.gui.update_gui()
            self.update_progress_window()
            time.sleep(0.1)

        self.progressButton.set_label("Close")
        self.progressButton.set_sensitive(True)
        self.end_of_program = True

        # End of program

    def remount_readonly(self):

        # Remounts the USB stored in self.inputFolder as readonly
        usb_path = self.inputFolder
        cmd = f"pkexec sh {self.projectRoot}/usb_readonly.sh {usb_path} {usb_path}"
        returnval = (os.system(cmd))

        if returnval == 0:
            print(f"The USB drive at {usb_path} has been remounted as read-only.")
            return True
        
        else:
            return False

    def find_usb_devices(self):

        usb_drives = []
    
        # Get list of all mounted devices
        mount_output = subprocess.check_output(['mount']).decode('utf-8')
        lines = mount_output.split('\n')
        
        # Sort through them and find ones that look like USB
        for line in lines:
            if '/dev/sd' in line and ('/media/' in line or '/mnt/' in line):
                parts = line.split()
                device = parts[0]
                mountpoint = parts[2]
                # Isolate devices/ mountpoint
                usb_drives.append({'device': device, 'mountpoint': mountpoint})
        
        # Save for GUI to access and print to screen
        self.usb_drives = usb_drives

class OAuthHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):

        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/oauth2/callback":

            query_params = urllib.parse.parse_qs(parsed_path.query)
            code = query_params.get("code")
            state = query_params.get("state")

            if code and state:

                try:

                    correct_qps = {"code": code[0], "state": state[0]}
                    oauth_result = dems.redirect_auth_flow.finish(correct_qps)
                    dems.access_token = oauth_result.access_token
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"Authorisation completed successfully, you may close this window and return to DEMS.")
                    print(dems.access_token)
                
                except Exception as e:

                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()     
                    self.wfile.write(f"The authorisation failed :\n\n{e}")

            else:

                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()     
                    self.wfile.write(b"Missing authorisation code.")

        dems.auth_in_progress = False


if __name__ == "__main__":

    dems = DEMS()
    dems.gui_interface()