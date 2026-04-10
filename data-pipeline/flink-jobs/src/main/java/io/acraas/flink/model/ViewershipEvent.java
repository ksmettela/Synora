package io.acraas.flink.model;

import java.io.Serializable;

public class ViewershipEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    public String deviceId;
    public String contentId;
    public String title;
    public String network;
    public String genre;
    public float matchConfidence;
    public long watchStartUtc;
    public int durationSec;
    public String manufacturer;
    public String model;
    public String ipAddress;

    public ViewershipEvent() {
    }

    public ViewershipEvent(String deviceId, String contentId, String title, String network,
                          String genre, float matchConfidence, long watchStartUtc,
                          int durationSec, String manufacturer, String model, String ipAddress) {
        this.deviceId = deviceId;
        this.contentId = contentId;
        this.title = title;
        this.network = network;
        this.genre = genre;
        this.matchConfidence = matchConfidence;
        this.watchStartUtc = watchStartUtc;
        this.durationSec = durationSec;
        this.manufacturer = manufacturer;
        this.model = model;
        this.ipAddress = ipAddress;
    }

    @Override
    public String toString() {
        return "ViewershipEvent{" +
                "deviceId='" + deviceId + '\'' +
                ", contentId='" + contentId + '\'' +
                ", title='" + title + '\'' +
                ", network='" + network + '\'' +
                ", genre='" + genre + '\'' +
                ", matchConfidence=" + matchConfidence +
                ", watchStartUtc=" + watchStartUtc +
                ", durationSec=" + durationSec +
                ", manufacturer='" + manufacturer + '\'' +
                ", model='" + model + '\'' +
                ", ipAddress='" + ipAddress + '\'' +
                '}';
    }
}
