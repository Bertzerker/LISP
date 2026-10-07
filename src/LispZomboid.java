import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.Field;
import java.util.Arrays;

/** Supply the engine's admin option from a private file instead of process arguments. */
public class LispZomboid {
    public static void main(String[] args) throws Exception {
        Path credential = Path.of(args[0]);
        String password = Files.readString(credential, StandardCharsets.UTF_8);
        Class<?> database = Class.forName("zombie.network.ServerWorldDatabase");
        Field instance = database.getField("instance");
        Field option = database.getField("commandLineAdminPassword");
        option.set(instance.get(null), password);
        Files.delete(credential);
        Class.forName("zombie.network.GameServer").getMethod("main", String[].class)
            .invoke(null, (Object)Arrays.copyOfRange(args, 1, args.length));
    }
}
