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
        p = self.getBluezProps()
        s = '{} ({})'.format(p.get('Name', 'Unnamed'), p['Address'])
        s += '\n   '
        s += '{}, {}'.format(
            'paired' if p['Paired'] else 'unpaired',
            'connected' if p['Connected'] else 'disconnected')
        return s

class BluetoothBrowser:
    """Bluetooth browser main widget"""
    palette = [
        ('item normal','', '', 'standout'),
        ('item select', 'black', 'dark green'),
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

    def bluetooth_device_paths(self):
        for s in dbus_child_paths(self.hci_object):
            yield '/'.join([self.hci_path, s])

    def in_list(self, widget):
        return urwid.AttrWrap(widget, \
                            'item normal', 'item select')

    def setup_view(self):
        """return a widget as the root widget"""
        self.powered_checkbox = self.in_list(urwid.CheckBox("power (To be implemented)",
            on_state_change=self.cb_power
            ))
        self.scanning_checkbox = self.in_list(urwid.CheckBox("scanning",
            on_state_change=self.cb_scan
            ))
        self.list_widgets = \
            [self.powered_checkbox,
             self.scanning_checkbox] \
            + [self.create_device_item(p)
             for p in self.bluetooth_device_paths()]
        self.devices_walker = urwid.SimpleFocusListWalker(self.list_widgets)
        self.devicesList = urwid.ListBox(self.devices_walker)
        self.update_status()
        return self.devicesList

    def cb_power(self, cb, new_state):
        prop_iface = dbus.Interface(self.hci_object, 'org.freedesktop.DBus.Properties')
        prop_iface.Set('org.bluez.Adapter1', 'Powered', new_state)
        pass

    def cb_scan(self, cb, new_state):
        bluez_iface = dbus.Interface(self.hci_object, 'org.bluez.Adapter1')
        if not self.properties['Powered']:
            # FIXME: Show some status message
            return
        if new_state:
            bluez_iface.StartDiscovery()
        else:
            bluez_iface.StopDiscovery()

    def update_status(self):
        prop_iface = dbus.Interface(self.hci_object, 'org.freedesktop.DBus.Properties')
        self.properties = prop_iface.GetAll('org.bluez.Adapter1')
        self.powered_checkbox.set_state(self.properties['Powered'],
            do_callback=False)
        self.scanning_checkbox.set_state(self.properties['Discovering'],
            do_callback=False)


    def create_device_item(self, object_path):
        w = DeviceWidget(self.bus.get_object(self.service, object_path))
        w = urwid.AttrWrap(w, 'item normal', 'item select')
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
