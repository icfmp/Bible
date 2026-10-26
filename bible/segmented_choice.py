"""Direct, mutually exclusive native choices without a popup or hidden options."""
from gi.repository import Gtk, GObject


class SegmentedChoice(Gtk.Box):
    __gsignals__={'changed':(GObject.SignalFlags.RUN_LAST,None,())}
    def __init__(self,labels,selected=0):
        super().__init__(spacing=0)
        self.add_css_class('linked');self.buttons=[];self._selected=selected;self._syncing=False
        for index,label in enumerate(labels):
            button=Gtk.ToggleButton(label=label)
            if self.buttons:button.set_group(self.buttons[0])
            button.set_active(index==selected)
            button.connect('toggled',self._toggled,index)
            self.append(button);self.buttons.append(button)
    def get_selected(self):return self._selected
    def set_selected(self,index):
        if index==self._selected:return
        self._syncing=True;self._selected=index;self.buttons[index].set_active(True);self._syncing=False
        self.emit('changed')
    def _toggled(self,button,index):
        if self._syncing or not button.get_active():return
        if self._selected!=index:self._selected=index;self.emit('changed')
