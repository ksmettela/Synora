package io.acraas.flink.model;

import java.io.Serializable;

public class EnrichedViewershipEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    public String deviceId;
    public String householdId;
    public String contentId;
    public String title;
    public String network;
    public String genre;
    public float matchConfidence;
    public long watchStartUtc;
    public int durationSec;
    public String watchDate;
    public int watchHour;
    public int durationMinutes;
    public String dmaCode;
    public String zipCode;
    public String manufacturer;
    public String model;
    public String ipAddress;

    public EnrichedViewershipEvent() {
    }

    public EnrichedViewershipEvent(String deviceId, String householdId, String contentId, String title,
                                   String network, String genre, float matchConfidence, long watchStartUtc,
                                   int durationSec, String watchDate, int watchHour, int durationMinutes,
                                   String dmaCode, String zipCode, String manufacturer, String model, String ipAddress) {
        this.deviceId = deviceId;
        this.householdId = householdId;
        this.contentId = contentId;
        this.title = title;
        this.network = network;
        this.genre = genre;
        this.matchConfidence = matchConfidence;
        this.watchStartUtc = watchStartUtc;
        this.durationSec = durationSec;
        this.watchDate = watchDate;
        this.watchHour = watchHour;
        this.durationMinutes = durationMinutes;
        this.dmaCode = dmaCode;
        this.zipCode = zipCode;
        this.manufacturer = manufacturer;
        this.model = model;
        this.ipAddress = ipAddress;
    }

    @Override
    public String toString() {
        return "EnrichedViewershipEvent{" +
                "deviceId='" + deviceId + '\'' +
                ", householdId='" + householdId + '\'' +
                ", contentId='" + contentId + '\'' +
                ", title='" + title + '\'' +
                ", network='" + network + '\'' +
                ", genre='" + genre + '\'' +
                ", matchConfidence=" + matchConfidence +
                ", watchStartUtc=" + watchStartUtc +
                ", durationSec=" + durationSec +
                ", watchDate='" + watchDate + '\'' +
                ", watchHour=" + watchHour +
                ", durationMinutes=" + durationMinutes +
                ", dmaCode='" + dmaCode + '\'' +
                ", zipCode='" + zipCode + '\'' +
                ", manufacturer='" + manufacturer + '\'' +
                ", model='" + model + '\'' +
                ", ipAddress='" + ipAddress + '\'' +
                '}';
    }
}
