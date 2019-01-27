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


class DeviceWidget(urwid.Text):
    def __init__(self, proxy_object):
        self.proxy_object = proxy_object
        self.properties = dbus.Interface(proxy_object, 'org.freedesktop.DBus.Properties')
        super(DeviceWidget, self).__init__(self.getDisplayLabel())

    def getBluezProp(self, prop_name):
        return self.properties.Get('org.bluez.Device1', prop_name)

    def getBluezProps(self):
        return self.properties.GetAll('org.bluez.Device1')

    def getDisplayLabel(self):
        def bool2str(b):
            return 'x' if b else ' '
        p = self.getBluezProps()
        s = '{} ({})'.format(p['Name'], p['Address'])
        s += '\n   '
        s += '{}, {}'.format(
            'paired' if p['Paired'] else 'unpaired',
            'connected' if p['Connected'] else 'disconnected')
        return s


class BluetoothBrowser:
    """Bluetooth browser main widget"""
    palette = [
        ('device normal','', '', 'standout'),
        ('device select', 'black', 'dark green'),
        ]
    def __init__(self, bus, service, hci_path):
        """
        bus is the dbus bus
        service is the service name
        object_path is the main object path
        """
        self.bus = bus
        self.hci_path = hci_path
        self.service = service
        self.hci_object = bus.get_object(service, self.hci_path)
        self.device_widgets = [self.create_device_item(p)
                               for p in self.bluetooth_device_paths()]

    def bluetooth_device_paths(self):
        for s in dbus_child_paths(self.hci_object):
            yield '/'.join([self.hci_path, s])

    def setup_view(self):
        """return a widget as the root widget"""
        self.devices_walker = urwid.SimpleFocusListWalker(self.device_widgets)
        self.devicesList = urwid.ListBox(self.devices_walker)
        return self.devicesList

    def create_device_item(self, object_path):
        w = DeviceWidget(self.bus.get_object(self.service, object_path))
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
    BluetoothBrowser(bus, 'org.bluez', '/org/bluez/hci0').main()
    return 0

sys.exit(main())
