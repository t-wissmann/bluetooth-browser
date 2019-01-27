#!/usr/bin/env python3
import sys
import urwid
import dbus.service
from gi.repository import GObject
from dbus.mainloop.glib import DBusGMainLoop
from xml.etree import ElementTree

def dbus_child_paths(obj):
    """return the names of all children of a given object_path"""
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')
    xml_string = iface.Introspect()
    for child in ElementTree.fromstring(xml_string):
        if child.tag == 'node':
            yield child.attrib['name']

class BluetoothDevice:
    """Wraper around a device that can be accessed via bluetooth"""
    def __init__(self):
        pass


class DeviceWidget:
    def __init__(self):
        pass


class BluetoothBrowser:
    """Bluetooth browser main widget"""
    palette = [
        ('device normal','', '', 'standout'),
        ('device select', 'black', 'dark green'),
        ]
    def __init__(self, dbus_proxy):
        """
        dbus_proxy is a proxy object to the bluetooth device, hci0
        """
        self.devices = [self.create_device_item(str(s))
                        for s in dbus_child_paths(dbus_proxy)]
        self.dbus_proxy = dbus_proxy

    def setup_view(self):
        """return a widget as the root widget"""
        self.devices_walker = urwid.SimpleFocusListWalker(self.devices)
        self.devicesList = urwid.ListBox(self.devices_walker)
        return self.devicesList

    def create_device_item(self, name):
        w = urwid.Text(name)
        w = urwid.AttrWrap(w, 'device normal', 'device select')
        return w

    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        if key == 'k':
            try:
                self.devicesList.set_focus(self.devicesList.focus_position - 1)
            except IndexError:
                pass
        if key == 'j':
            try:
                self.devicesList.set_focus(self.devicesList.focus_position + 1)
            except IndexError:
                pass
        if key == 'g':
            self.devicesList.set_focus(0)
        if key == 'G':
            self.devicesList.set_focus(len(self.devices) - 1)

    def main(self):
        widget = self.setup_view()
        loop = urwid.MainLoop(widget, self.palette,
                              unhandled_input=self.unhandled_input,
                              event_loop=urwid.GLibEventLoop())
        loop.run()

def main():
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    proxy = bus.get_object('org.bluez', '/org/bluez/hci0')
    BluetoothBrowser(proxy).main()
    return 0

sys.exit(main())
