package io.acraas.flink.serde;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.acraas.flink.model.ViewershipEvent;
import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

public class ViewershipEventDeserializer implements DeserializationSchema<ViewershipEvent> {
    private static final Logger LOG = LoggerFactory.getLogger(ViewershipEventDeserializer.class);
    private transient ObjectMapper mapper;

    @Override
    public void open(InitializationContext context) throws Exception {
        mapper = new ObjectMapper();
    }

    @Override
    public ViewershipEvent deserialize(byte[] message) throws IOException {
        try {
            return mapper.readValue(message, ViewershipEvent.class);
        } catch (Exception e) {
            LOG.error("Failed to deserialize viewership event: {}", new String(message), e);
            throw new IOException("Deserialization failed", e);
        }
    }

    @Override
    public boolean isEndOfStream(ViewershipEvent nextElement) {
        return false;
    }

    @Override
    public TypeInformation<ViewershipEvent> getProducedType() {
        return TypeInformation.of(ViewershipEvent.class);
    }
}
