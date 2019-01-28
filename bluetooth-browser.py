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
    def __init__(self, proxy_object, parent):
        self.proxy_object = proxy_object
        self.prop_iface = dbus.Interface(proxy_object, 'org.freedesktop.DBus.Properties')
        self.properties = self.prop_iface.GetAll('org.bluez.Device1')
        super(DeviceWidget, self).__init__(self.getDisplayLabel())
        self.prop_iface.connect_to_signal('PropertiesChanged', self.on_properties_changed)
        self.parent = parent # the parent widget with a redraw-method

    def on_properties_changed(self, iface, new_values, sender=None):
        if iface != 'org.bluez.Device1':
            return
        for k, v in new_values.items():
            self.properties[k] = v
        super(DeviceWidget, self).set_text(self.getDisplayLabel())
        self.parent.redraw()

    def getDisplayLabel(self):
        p = self.properties
        s = '{} ({})'.format(p.get('Name', 'Unnamed'), p['Address'])
        s += '\n   '
        s += '{}, {}'.format(
            'paired' if p['Paired'] else 'unpaired',
            'connected' if p['Connected'] else 'disconnected')
        return s

    def on_key(self, key):
        iface = dbus.Interface(self.proxy_object, 'org.bluez.Device1')
        if key == 'enter':
            if self.properties['Paired'] and not self.properties['Connected']:
                iface.Connect()
            elif not self.properties['Paired'] :
                iface.Pair()
        if key == 'd':
            if self.properties['Connected']:
                iface.Disconnect()

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
        iface = dbus.Interface(self.hci_object, 'org.freedesktop.DBus.Properties')
        self.properties = iface.GetAll('org.bluez.Adapter1')
        iface.connect_to_signal('PropertiesChanged', self.on_properties_changed)

    def bluetooth_device_paths(self):
        for s in dbus_child_paths(self.hci_object):
            yield '/'.join([self.hci_path, s])

    def in_list(self, widget):
        return urwid.AttrMap(widget, \
                            'item normal', 'item select')

    def setup_view(self):
        """return a widget as the root widget"""
        self.powered_checkbox = urwid.CheckBox("power",
            on_state_change=self.cb_power)
        self.scanning_checkbox = urwid.CheckBox("scanning",
            on_state_change=self.cb_scan)
        self.list_widgets = \
            [self.powered_checkbox,
             self.scanning_checkbox] \
            + [self.create_device_item(p)
             for p in self.bluetooth_device_paths()]
        self.list_widgets = [ self.in_list(w) for w in self.list_widgets]
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

    def on_properties_changed(self, iface, new_values, sender=None):
        if iface != 'org.bluez.Adapter1':
            return
        #print(new_values, file=sys.stderr)
        for k, v in new_values.items():
            self.properties[k] = v
        self.update_status()
        self.loop.draw_screen()

    def update_status(self):
        self.powered_checkbox.set_state(self.properties['Powered'],
            do_callback=False)
        self.scanning_checkbox.set_state(self.properties['Discovering'],
            do_callback=False)


    def create_device_item(self, object_path):
        w = DeviceWidget(self.bus.get_object(self.service, object_path), self)
        return w

    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        elif key == 'k':
            try:
                self.devicesList.set_focus(self.devicesList.focus_position - 1)
            except IndexError:
                pass
        elif key == 'j':
            try:
                self.devicesList.set_focus(self.devicesList.focus_position + 1)
            except IndexError:
                pass
        elif key == 'g':
            self.devicesList.set_focus(0)
        elif key == 'G':
            self.devicesList.set_focus(len(self.devices) - 1)
        else:
            w,_ = focus = self.devicesList.get_focus()
            w = w.original_widget
            #print(str(w), file=sys.stderr)
            if isinstance(w, DeviceWidget):
                w.on_key(key)

    def redraw(self):
        self.loop.draw_screen()
    def main(self):
        widget = self.setup_view()
        self.loop = urwid.MainLoop(widget, self.palette,
                              unhandled_input=self.unhandled_input,
                              event_loop=urwid.GLibEventLoop())
        self.loop.run()

def main():
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    BluetoothBrowser(bus, 'org.bluez', '/org/bluez/hci0').main()
    return 0

sys.exit(main())
