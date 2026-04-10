package io.acraas.flink.enrichment;

import io.acraas.flink.model.ViewershipEvent;
import io.acraas.flink.model.EnrichedViewershipEvent;
import org.apache.flink.api.common.functions.MapFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;

public class HouseholdEnricher implements MapFunction<ViewershipEvent, EnrichedViewershipEvent> {
    private static final Logger LOG = LoggerFactory.getLogger(HouseholdEnricher.class);

    private transient SimpleDateFormat dateFormat;
    private transient SimpleDateFormat hourFormat;
    private transient MessageDigest messageDigest;

    @Override
    public void open(org.apache.flink.configuration.Configuration parameters) throws Exception {
        dateFormat = new SimpleDateFormat("yyyy-MM-dd");
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        hourFormat = new SimpleDateFormat("HH");
        hourFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        messageDigest = MessageDigest.getInstance("SHA-256");
    }

    @Override
    public EnrichedViewershipEvent map(ViewershipEvent event) throws Exception {
        String householdId = deriveHouseholdId(event.deviceId, event.ipAddress);

        Date watchTime = new Date(event.watchStartUtc * 1000);
        String watchDate = dateFormat.format(watchTime);
        int watchHour = Integer.parseInt(hourFormat.format(watchTime));

        int durationMinutes = event.durationSec / 60;

        String dmaCode = "00000";
        String zipCode = "00000";

        return new EnrichedViewershipEvent(
            event.deviceId,
            householdId,
            event.contentId,
            event.title,
            event.network,
            event.genre,
            event.matchConfidence,
            event.watchStartUtc,
            event.durationSec,
            watchDate,
            watchHour,
            durationMinutes,
            dmaCode,
            zipCode,
            event.manufacturer,
            event.model,
            event.ipAddress
        );
    }

    private String deriveHouseholdId(String deviceId, String ipAddress) {
        try {
            String subnet = extractSubnet(ipAddress);
            String input = deviceId + "|" + subnet;

            messageDigest.reset();
            byte[] hash = messageDigest.digest(input.getBytes(StandardCharsets.UTF_8));

            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }

            return "hh_" + hexString.toString().substring(0, 16);
        } catch (Exception e) {
            LOG.warn("Error deriving household ID for device {}, using device ID as fallback", deviceId, e);
            return "hh_" + deviceId.replace("-", "").substring(0, 16);
        }
    }

    private String extractSubnet(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return "0.0.0";
        }

        String[] parts = ipAddress.split("\\.");
        if (parts.length \!= 4) {
            return "0.0.0";
        }

        return parts[0] + "." + parts[1] + "." + parts[2];
    }
}
