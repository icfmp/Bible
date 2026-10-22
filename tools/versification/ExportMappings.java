import java.lang.reflect.*;
import java.util.*;
import org.crosswire.jsword.versification.*;
import org.crosswire.jsword.versification.system.Versifications;
import org.crosswire.jsword.passage.*;

/** Export the pinned upstream parser's actual data, not a second properties parser. */
public class ExportMappings {
 static Object field(Object o,String n) throws Exception { Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o); }
 static List<String> refs(VerseKey k) { List<String> a=new ArrayList<>();for(Iterator<Key> i=k.iterator();i.hasNext();)a.add(((Verse)i.next()).getOsisRef());return a; }
 static List<String> qualified(QualifiedKey q) throws Exception {
  if(q.getKey()==null)return Arrays.asList(q.getSectionName());
  VerseKey k=(VerseKey)field(q,"qualifiedKey");
  if(!q.isWhole())return Arrays.asList(k.getOsisRef());
  return refs(k);
 }
 static String json(Object o) {
  if(o==null)return "null";
  if(o instanceof String)return "\""+((String)o).replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\"";
  if(o instanceof Map){List<String>a=new ArrayList<>();((Map<?,?>)o).forEach((k,v)->a.add(json(k)+":"+json(v)));return "{"+String.join(",",a)+"}";}
  if(o instanceof Iterable){List<String>a=new ArrayList<>();for(Object v:(Iterable<?>)o)a.add(json(v));return "["+String.join(",",a)+"]";}
  return o.toString();
 }
 public static void main(String[] args) throws Exception {
  Map<String,Object> all=new TreeMap<>();
  for(String name:args) {
   Versification v=Versifications.instance().getVersification(name);
   Map<String,Object> canon=new LinkedHashMap<>(),row=new TreeMap<>();
   for(Iterator<BibleBook> i=v.getBookIterator();i.hasNext();) {
    BibleBook b=i.next();List<Integer> sizes=new ArrayList<>();
    for(int c=1;c<=v.getLastChapter(b);c++)sizes.add(v.getLastVerse(b,c));
    if(!sizes.isEmpty())canon.put(b.getOSIS(),sizes);
   }
   row.put("canon",canon);
   if(!name.equals("KJVA")&&!name.equals("KJV")) {
    VersificationToKJVMapper mapper=new VersificationToKJVMapper(v,new FileVersificationMapping(v));
    if((Boolean)field(mapper,"hasErrors"))throw new IllegalStateException("Errors loading "+name);
    Map<String,Object> forward=new TreeMap<>(),reverse=new TreeMap<>();
    Map<VerseKey,List<QualifiedKey>> fm=(Map<VerseKey,List<QualifiedKey>>)field(mapper,"toKJVMappings");
    for(Map.Entry<VerseKey,List<QualifiedKey>> e:fm.entrySet()) {
     List<String> keys=new ArrayList<>();for(QualifiedKey q:e.getValue())keys.addAll(qualified(q));
     forward.put(e.getKey().getOsisRef(),keys);
    }
    Map<QualifiedKey,Passage> rm=(Map<QualifiedKey,Passage>)field(mapper,"fromKJVMappings");
    for(Map.Entry<QualifiedKey,Passage> e:rm.entrySet()) {
     List<String> keys=qualified(e.getKey());if(keys.size()!=1)throw new IllegalStateException("non-single reverse");
     reverse.put(keys.get(0),refs(e.getValue()));
    }
    row.put("forward",forward);row.put("reverse",reverse);row.put("absent",refs((VerseKey)field(mapper,"absentVerses")));
   }
   all.put(name,row);
  }
  System.out.println(json(all));
 }
}
