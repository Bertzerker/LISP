import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.lang.reflect.Method;

/** Verify only an owned test account using the installed engine's password transform. */
public class CheckZomboidAdmin {
 public static void main(String[] args) throws Exception {
  String password = null;
  for(String line: Files.readAllLines(Path.of(args[0]),StandardCharsets.UTF_8))
   if(line.startsWith("RCONPassword=")) password=line.substring("RCONPassword=".length());
  if(password==null || password.isEmpty()) throw new AssertionError("Test server is not configured");
  Class.forName("org.sqlite.JDBC");
  try(Connection db=DriverManager.getConnection("jdbc:sqlite:file:"+args[1]+"?mode=ro")) {
   ResultSet row=db.createStatement().executeQuery("select password,role from whitelist where username='admin'");
   if(!row.next()) throw new AssertionError("Admin account missing");
   String hash=row.getString(1);
   Method encrypt=Class.forName("zombie.network.ServerWorldDatabase").getMethod("encrypt",String.class);
   String encoded=(String)encrypt.invoke(null,password);
   Method check=Class.forName("org.mindrot.jbcrypt.BCrypt").getMethod("checkpw",String.class,String.class);
   if(!(Boolean)check.invoke(null,encoded,hash)) throw new AssertionError("Native admin password does not match");
   String wrong=(String)encrypt.invoke(null,"WrongTestPassword");
   if((Boolean)check.invoke(null,wrong,hash)) throw new AssertionError("Wrong admin password matched");
   System.out.println("PASS native admin password hash, wrong-password rejection and role "+row.getString(2));
  }
 }
}
