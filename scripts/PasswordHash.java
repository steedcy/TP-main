import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.io.Console;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** One-time deployment helper. Reads the password from a terminal without echoing it. */
public final class PasswordHash {
    private PasswordHash() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: PasswordHash <private-output-file>");
            System.exit(2);
        }
        Console console = System.console();
        if (console == null) {
            System.err.println("Run this helper from an interactive terminal.");
            System.exit(2);
        }
        char[] password = console.readPassword("Initial administrator password (12+ characters): ");
        char[] confirm = console.readPassword("Confirm password: ");
        try {
            if (password == null || password.length < 12 || !Arrays.equals(password, confirm)) {
                System.err.println("Password confirmation failed or password is shorter than 12 characters.");
                System.exit(2);
            }
            String hash = new BCryptPasswordEncoder().encode(new String(password));
            Files.writeString(Path.of(args[0]), hash);
        } finally {
            if (password != null) Arrays.fill(password, '\0');
            if (confirm != null) Arrays.fill(confirm, '\0');
        }
    }
}
