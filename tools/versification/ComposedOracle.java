import java.io.*;import java.util.*;
import org.crosswire.jsword.versification.*;import org.crosswire.jsword.versification.system.*;import org.crosswire.jsword.passage.*;
/** Upstream map/unmap APIs, with whole groups explicitly composed verse by verse.
 * Avoids top-level range identity fallback and reports unsupported qualified ranges.
 */
public class ComposedOracle {
 static final Map<String,VersificationToKJVMapper> MAP=new HashMap<>();
 static final Versification BASE=Versifications.instance().getVersification("KJVA");
 static VersificationToKJVMapper mapper(Versification v)throws Exception {
  if(v.equals(BASE)||v.getName().equals("KJV"))return null;
  if(!MAP.containsKey(v.getName()))MAP.put(v.getName(),new VersificationToKJVMapper(v,new FileVersificationMapping(v)));
  return MAP.get(v.getName());
 }
 public static void main(String[] args)throws Exception {
  BufferedReader in=new BufferedReader(new InputStreamReader(System.in));String line;
  while((line=in.readLine())!=null) {
   String[] r=line.split("\t");Versification s=Versifications.instance().getVersification(r[0]),t=Versifications.instance().getVersification(r[2]);
   Verse source=VerseFactory.fromString(s,r[1]);List<QualifiedKey> base;
   VersificationToKJVMapper sm=mapper(s),tm=mapper(t);
   if(sm==null)base=Arrays.asList(QualifiedKey.create(source.reversify(BASE)));else base=sm.map(QualifiedKey.create(source));
   Set<String> result=new TreeSet<>();boolean unsupported=false;
   for(QualifiedKey group:base) {
    List<QualifiedKey> parts=new ArrayList<>();
    if(group.getKey()!=null&&group.getKey().getCardinality()>1) {
     if(!group.isWhole()){unsupported=true;break;}
     for(Iterator<Key> it=group.getKey().iterator();it.hasNext();)parts.add(QualifiedKey.create((Verse)it.next()));
    }else parts.add(group);
    for(QualifiedKey q:parts) {
     VerseKey mapped=tm==null?(q.getKey()==null?null:q.getKey().reversify(t)):tm.unmap(q);
     if(mapped!=null)for(Iterator<Key> it=mapped.iterator();it.hasNext();)result.add(((Verse)it.next()).getOsisRef());
    }
   }
   System.out.println(line+"\t"+(unsupported?"UNSUPPORTED":String.join(",",result)));
  }
 }
}
