#!/bin/bash

#tshark -r pcap_1__MLKEM768.pcap -o tls.keylog_file:keylog_1__MLKEM768.txt -Y "tls.handshake" -T fields -e frame.number -e frame.time_epoch -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tls.handshake.type -e tls.handshake.length -e frame.len -E header=y -E separator=, -E quote=d -E occurrence=a \

#tshark -r pcap_1__MLKEM768.pcap -o tls.keylog_file:keylog_1__MLKEM768.txt -Y "tls.record" -T fields -e frame.number -e frame.time_epoch -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tls.record.content_type -e tls.record.length -e frame.len -E header=y -E separator=, -E quote=d -E occurrence=a


tshark -r pcap_1_falcon512_MLKEM768.pcap \
  -o tls.keylog_file:keylog_1_falcon512_MLKEM768.txt \
  -o tcp.desegment_tcp_streams:TRUE \
  -o tls.desegment_ssl_records:TRUE \
  -o tls.desegment_ssl_application_data:TRUE \
  -Y "tls.handshake.type" -T fields \
  -e frame.number -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport \
  -e tls.handshake.type -e tls.handshake.length \
  -E header=y -E separator=, -E quote=d -E occurrence=a