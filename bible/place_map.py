"""Native Cairo overview of actual coastline/candidate data, without tile requests."""
import math
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,Gdk
from .i18n import tr


def extent(candidates,width=700,height=200):
    located=[c for c in candidates if c['longitude'] is not None]
    if not located:return None
    xs=[c['longitude'] for c in located];ys=[c['latitude'] for c in located]
    lon=(min(xs)+max(xs))/2;lat=(min(ys)+max(ys))/2
    dx=max(.5 if len(located)>1 else 4,(max(xs)-min(xs))*1.15+.1)
    dy=max(.4 if len(located)>1 else 3,(max(ys)-min(ys))*1.15+.1)
    ratio=max(.15,math.cos(math.radians(lat)));aspect=max(1,width)/max(1,height)
    if dx*ratio/dy<aspect:dx=dy*aspect/ratio
    else:dy=dx*ratio/aspect
    dx=min(360,dx);dy=min(180,dy)
    west=max(-180,min(lon-dx/2,180-dx));south=max(-90,min(lat-dy/2,90-dy))
    return west,south,west+dx,south+dy


class PlaceMap(Gtk.DrawingArea):
    def __init__(self):
        super().__init__(hexpand=True,height_request=220)
        self.lines=[];self.candidates=[]
        self.set_draw_func(self.draw)
        self.update_property([Gtk.AccessibleProperty.LABEL],
            [tr('Geographical overview. Candidate coordinates and uncertainty are listed below.')])
        self.set_tooltip_text(tr('Simplified modern coastlines; not a historical or street map.'))

    def set_data(self,lines,candidates):
        self.lines=lines;self.candidates=[c for c in candidates if c['longitude'] is not None]
        self.queue_draw()

    def color(self,name,fallback):
        found,color=self.get_style_context().lookup_color(name)
        if found:return color
        found,color=self.get_style_context().lookup_color(fallback)
        return color if found else self.get_style_context().get_color()

    def draw(self,widget,cr,width,height):
        # The existing runtime supplies PyCairo/its GI foreign converter.
        from gi.repository import PangoCairo
        bounds=extent(self.candidates,width,height)
        bg=self.color('view_bg_color','window_bg_color');Gdk.cairo_set_source_rgba(cr,bg);cr.paint()
        if not bounds:return
        west,south,east,north=bounds
        def point(lon,lat):return ((lon-west)/(east-west)*width,(north-lat)/(north-south)*height)
        cr.save();cr.rectangle(0,0,width,height);cr.clip()
        fg=self.color('view_fg_color','window_fg_color')
        cr.set_source_rgba(fg.red,fg.green,fg.blue,.12);cr.set_line_width(1)
        for fraction in (.25,.5,.75):
            cr.move_to(width*fraction,0);cr.line_to(width*fraction,height)
            cr.move_to(0,height*fraction);cr.line_to(width,height*fraction)
        cr.stroke()
        cr.set_source_rgba(fg.red,fg.green,fg.blue,.55);cr.set_line_width(1)
        for line in self.lines:
            first=True;previous=None
            for lon,lat in line:
                x,y=point(lon,lat)
                if first or previous is not None and abs(lon-previous)>180:cr.move_to(x,y)
                else:cr.line_to(x,y)
                first=False;previous=lon
            cr.stroke()
        # Source roles stay visible in the text list; unlocated alternatives
        # never acquire a marker. Numbers identify actual candidate records.
        accent=self.color('accent_bg_color','accent_color');ink=self.color('accent_fg_color','view_bg_color')
        groups=[]
        for index,candidate in enumerate(self.candidates):
            x,y=point(candidate['longitude'],candidate['latitude'])
            group=next((g for g in groups if math.hypot(g['x']-x,g['y']-y)<24),None)
            if group is None:groups.append(dict(x=x,y=y,numbers=[candidate.get('number',index+1)]))
            else:group['numbers'].append(candidate.get('number',index+1))
        for group in groups:
            x,y=group['x'],group['y']
            label=','.join(map(str,group['numbers'])) if len(group['numbers'])<=3 else str(len(group['numbers']))+'×'
            layout=self.create_pango_layout(label)
            text_width,text_height=layout.get_pixel_size();radius=max(10,text_width/2+4,text_height/2+2)
            Gdk.cairo_set_source_rgba(cr,accent);cr.arc(x,y,radius,0,math.tau);cr.fill()
            Gdk.cairo_set_source_rgba(cr,ink);cr.move_to(x-text_width/2,y-text_height/2);PangoCairo.show_layout(cr,layout)
        cr.restore()
