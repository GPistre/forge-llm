package forge.view;

/**
 * Utility class for downloading and managing BigQuery deck IDs.
 * This class provides helper methods for identifying and handling BigQuery deck IDs.
 */
public class DeckDownloader {
    
    /**
     * Checks if the given deck name looks like a BigQuery deck ID.
     * BigQuery deck IDs typically contain hyphens and follow a specific pattern.
     * 
     * @param deckname The deck name to check
     * @return true if the deck name looks like a BigQuery deck ID, false otherwise
     */
    public static boolean isBigQueryDeckId(String deckname) {
        if (deckname == null || deckname.trim().isEmpty()) {
            return false;
        }
        
        // BigQuery deck IDs typically contain hyphens and are alphanumeric
        // Examples: "moxfield-TdOsPBP3302BdskyLVzU-A", "archidekt-12345-deck-name"
        return deckname.contains("-") && 
               deckname.matches("^[a-zA-Z0-9\\-_]+$") && 
               deckname.length() > 5;
    }
    
    /**
     * Sanitizes a deck name/ID to be safe for use as a filename.
     * Removes or replaces characters that are not safe for filenames.
     * 
     * @param deckname The deck name to sanitize
     * @return A sanitized version of the deck name safe for use as a filename
     */
    public static String sanitizeFilename(String deckname) {
        if (deckname == null) {
            return "unknown_deck";
        }
        
        // Replace unsafe characters with underscores
        String sanitized = deckname.replaceAll("[^a-zA-Z0-9\\-_]", "_");
        
        // Remove multiple consecutive underscores
        sanitized = sanitized.replaceAll("_{2,}", "_");
        
        // Remove leading/trailing underscores
        sanitized = sanitized.replaceAll("^_+|_+$", "");
        
        // Ensure it's not empty
        if (sanitized.isEmpty()) {
            return "unknown_deck";
        }
        
        return sanitized;
    }
}