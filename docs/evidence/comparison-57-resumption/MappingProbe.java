import org.crosswire.jsword.versification.*;
import org.crosswire.jsword.versification.system.Versifications;
import org.crosswire.jsword.passage.*;
public class MappingProbe {
 public static void main(String[] args) throws Exception {
  String[][] rows={{"Luther","Gen.32.1","KJVA"},{"Luther","Ps.3.2","KJVA"},{"Segond","Ps.3.2","Luther"},{"Luther","1Sam.21.15","KJVA"},{"Luther","Acts.19.40","KJVA"}};
  for(String[] row: rows) {
   Versification source=Versifications.instance().getVersification(row[0]);
   Versification target=Versifications.instance().getVersification(row[2]);
   VerseKey result=VersificationsMapper.instance().mapVerse(VerseFactory.fromString(source,row[1]),target);
   System.out.println(row[0]+"\t"+row[1]+"\t"+row[2]+"\t"+result.getOsisRef());
  }
 }
}
