#!/bin/sh

# === CONFIG ===
BASE_FOLDER="/mnt/c/Users/marie/pqc/test_data/up_results/tls_performance/machine_1_messagesizes_test/traffic"
PCAP_DIR="$BASE_FOLDER/pqc"
OUTPUT_DIR="$PCAP_DIR/tls_stats"

mkdir -p "$OUTPUT_DIR"

# === iterate over all pcap files ===
for PCAP_FILE in "$PCAP_DIR"/*.pcap; do
    BASENAME=$(basename "$PCAP_FILE" .pcap)

    # Keylog-Datei automatisch ableiten
    KEYLOG_FILE="$PCAP_DIR/$(echo "$BASENAME" | sed 's/^pcap_/keylog_/').txt"

    # Sicherheitscheck
    if [ ! -f "$KEYLOG_FILE" ]; then
        echo "WARNING: Keylog file not found for $PCAP_FILE"
        echo "Expected: $KEYLOG_FILE"
        continue
    fi

    OUTPUT_CSV="$OUTPUT_DIR/${BASENAME}_tls_handshake_stats.csv"

    echo "Processing:"
    echo "  PCAP   : $PCAP_FILE"
    echo "  KEYLOG : $KEYLOG_FILE"
    echo "  OUTPUT : $OUTPUT_CSV"

    TMPFILE=$(mktemp /tmp/tls_handshake.XXXX)

    # === Extract TLS handshake data with tshark ===
    tshark -r "$PCAP_FILE" \
      -o tls.keylog_file:"$KEYLOG_FILE" \
      -o tcp.desegment_tcp_streams:FALSE \
      -o tls.desegment_ssl_records:FALSE \
      -o tls.desegment_ssl_application_data:FALSE \
      -Y "tls.handshake.type" -T fields \
      -e tcp.stream -e frame.number -e tls.handshake.type -e tls.handshake.length \
      > "$TMPFILE"

    # === Analyse & CSV output with robust awk ===
    awk '
    function type_name(t){
        t = t + 0
        if(t==1) return "ClientHello"
        if(t==2) return "ServerHello"
        if(t==8) return "EncryptedExtensions"
        if(t==11) return "Certificate"
        if(t==12) return "ServerKeyExchange"
        if(t==14) return "ServerHelloDone"
        if(t==15) return "ClientKeyExchange"
        if(t==20) return "Finished"
        return "Other_" t
    }
    {
        n = split($3, types, ",")
        split($4, lengths, ",")
        for(i=1; i<=n; i++){
            t = types[i] + 0
            l = lengths[i] + 0
            key = $1 "-" t
            packets[key]++
            msg_length[key] = l
            sum[t] += l
            count[t]++
        }
    }
    END {
        print "TLS Type,Num Messages,Min Len,Max Len,Avg Len,Avg Packets"
        for(t in count){
            min=999999
            max=0
            totp=0
            msgs=0
            for(k in msg_length){
                split(k,a,"-")
                if(a[2]+0 == t){
                    if(msg_length[k]<min) min=msg_length[k]
                    if(msg_length[k]>max) max=msg_length[k]
                    totp += packets[k]
                    msgs++
                }
            }
            printf "%s,%d,%d,%d,%.1f,%.2f\n",
                   type_name(t), msgs, min, max, sum[t]/count[t], totp/msgs
        }
    }' "$TMPFILE" > "$OUTPUT_CSV"

    rm "$TMPFILE"
done

echo "All PCAPs processed."
