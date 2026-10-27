"""On-demand native Shumate map; toolkit-owned tiles, cache and navigation."""
import math
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from .i18n import tr

gi.require_version('Shumate','1.0')
from gi.repository import Shumate
if (Shumate.MAJOR_VERSION,Shumate.MINOR_VERSION)<(1,4):
    raise ImportError('The map requires libshumate 1.4 or later; the Flatpak bundles 1.5.5.')

TILE_URL='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
COPYRIGHT_URL='https://www.openstreetmap.org/copyright'
USER_AGENT='Bible/0.1-alpha (+https://github.com/icfmp/Bible)'


def region(candidates,width=600,height=260):
    """Fit supplied candidate points; never infer a site or historical border."""
    xs=[(c['longitude']+180)/360 for c in candidates]
    ys=[(1-math.asinh(math.tan(math.radians(max(-85,min(85,c['latitude'])))))/math.pi)/2 for c in candidates]
    dx,dy=max(xs)-min(xs),max(ys)-min(ys)
    zoom=min(7,math.log2(min(max(100,width-80)/(256*max(dx,.001)),
                            max(100,height-80)/(256*max(dy,.001)))))
    lon=(min(xs)+max(xs))/2*360-180
    lat=math.degrees(math.atan(math.sinh(math.pi*(1-min(ys)-max(ys)))))
    return lat,lon,max(2,zoom)


class PlaceMap(Gtk.Box):
    def __init__(self,candidates):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=6,hexpand=True)
        self.candidates=tuple(c for c in candidates if c['longitude'] is not None)
        self.canvas=None;self.layer=None;self._loaded_handler=0;self.ready=False
        self.status=Gtk.Label(label=tr('Loading map…'),xalign=0,wrap=True)
        self.status.add_css_class('caption');self.status.add_css_class('dim-label')
        self.retry=Gtk.Button(label=tr('Retry'),halign=Gtk.Align.START,visible=False)
        self.retry.connect('clicked',lambda *_:self.start())
        self.credit=Gtk.LinkButton(uri=COPYRIGHT_URL,label='© OpenStreetMap contributors',halign=Gtk.Align.START)
        self.credit.add_css_class('caption')
        self.append(self.credit);self.append(self.status);self.append(self.retry)
        self.connect('map',lambda *_:self.start() if self.canvas is None else None)
        self.connect('unmap',lambda *_:self.stop())

    def start(self):
        self.stop();self.ready=False;self.retry.set_visible(False)
        self.status.set_text(tr('Loading map…'));self.status.set_visible(True)
        Shumate.set_user_agent(USER_AGENT)
        self.canvas=Shumate.SimpleMap(hexpand=True,height_request=260)
        self.canvas.set_show_zoom_buttons(True)
        self.canvas.get_license().set_visible(False) # Replaced by the visible linked credit immediately below.
        self.canvas.update_property([Gtk.AccessibleProperty.LABEL],[tr('Modern map with proposed historical locations')])
        source=Shumate.RasterRenderer.new_full('bible-osm-standard','OpenStreetMap',
            '© OpenStreetMap contributors',COPYRIGHT_URL,2,18,256,Shumate.MapProjection.MERCATOR,
            Shumate.TileDownloader.new(TILE_URL))
        viewport=self.canvas.get_viewport()
        viewport.set_reference_map_source(source)
        lat,lon,zoom=region(self.candidates,max(300,self.get_width()))
        viewport.set_location(lat,lon);viewport.set_zoom_level(zoom)
        self.canvas.set_map_source(source)
        markers=Shumate.MarkerLayer.new(viewport)
        for index,candidate in enumerate(self.candidates):
            marker=Shumate.Marker();marker.set_location(candidate['latitude'],candidate['longitude'])
            if len(self.candidates)>1:
                child=Gtk.Label(label=str(index+1));child.add_css_class('heading');child.add_css_class('accent')
            else:child=Gtk.Image(icon_name='bible-place-symbolic',pixel_size=24)
            badge=Gtk.Box();badge.add_css_class('place-map-marker')
            for side in ('start','end','top','bottom'):getattr(child,'set_margin_'+side)(4)
            badge.append(child);marker.set_child(badge)
            from .place_names import place_name
            marker.set_tooltip_text(place_name(candidate.get('name','')) or tr('Proposed modern locations'))
            markers.add_marker(marker)
        self.canvas.add_overlay_layer(markers)
        self.layer=self.canvas.get_base_map_layer()
        self._loaded_handler=self.layer.connect('map-loaded',self.loaded)
        self.prepend(self.canvas)

    def loaded(self,layer,errors):
        if layer is not self.layer:return
        self.ready=not errors
        self.status.set_text(tr('Map unavailable offline or because of a connection error.') if errors else '')
        self.status.set_visible(bool(errors));self.retry.set_visible(bool(errors))

    def stop(self):
        if self.layer and self._loaded_handler:self.layer.disconnect(self._loaded_handler)
        self._loaded_handler=0
        if self.canvas:
            # Removing the native layer releases its tiles and pending work;
            # no custom downloader, periodic timer or background map survives.
            if self.layer:self.canvas.get_map().remove_layer(self.layer)
            self.remove(self.canvas)
        self.canvas=None;self.layer=None
