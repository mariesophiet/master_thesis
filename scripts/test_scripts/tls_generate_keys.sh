#!/bin/bash

# Copyright (c) 2023-2025 Callum Turino
# SPDX-License-Identifier: MIT

# Script for generating server certificates and keys for TLS handshake benchmarking.
# Generates classic, Post-Quantum, and Hybrid-PQC certificates using OpenSSL 3.5.0,
# using PQC implementations natively available in OpenSSL and those integrated via OQS-Provider.
# The generated key material must be copied to the client machine unless both client and server run on the same system.

#-------------------------------------------------------------------------------------------------------------------------------
function setup_base_env() {
    # Function for setting up the basic global variables for the script. This includes setting the root directory, the global
    # library paths for the test suite, and creating the algorithm arrays. The function establishes the root path by determining
    # the path of the script and using this, determines the root directory of the project.

    # Determine the directory that the script is being run from
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

    # Try and find the .dir_marker.tmp file to determine the project's root directory
    current_dir="$script_dir"

    # Continue moving up the directory tree until the .pqc_leo_dir_marker.tmp file is found
    while true; do

        # Check if the .pqc_leo_dir_marker.tmp file is present
        if [ -f "$current_dir/.pqc_leo_dir_marker.tmp" ]; then
            root_dir="$current_dir"
            break
        fi

        # Move up a directory and store the new path
        current_dir=$(dirname "$current_dir")

        # If the system's root directory is reached and the file is not found, exit the script
        if [ "$current_dir" == "/" ]; then
            echo -e "Root directory path file not present, please ensure the path is correct and try again."
            exit 1
        fi

    done

    # Declare the main directory path variables based on the project's root dir
    libs_dir="$root_dir/lib"
    tmp_dir="$root_dir/tmp"
    test_data_dir="$root_dir/test_data"
    util_scripts="$root_dir/scripts/utility_scripts"

    # Declare the global library directory path variables
    openssl_path="$libs_dir/openssl_3.5.0"
    oqs_provider_path="$libs_dir/oqs_provider"

    # Ensure that the OQS-Provider and OpenSSL libraries are present before proceeding
    if [ ! -d "$oqs_provider_path" ]; then
        echo "[ERROR] - OQS-Provider library not found in $libs_dir"
        exit 1

    elif [ ! -d "$openssl_path" ]; then
        echo "[ERROR] - OpenSSL library not found in $libs_dir"
        exit 1
    fi

    # Check the OpenSSL library directory path
    if [[ -d "$openssl_path/lib64" ]]; then
        openssl_lib_path="$openssl_path/lib64"
    else
        openssl_lib_path="$openssl_path/lib"
    fi

    # Export the OpenSSL library filepath
    export LD_LIBRARY_PATH="$openssl_lib_path:$LD_LIBRARY_PATH"

    # Declare global key storage directory paths
    keys_dir="$test_data_dir/keys"
    pqc_cert_dir="$keys_dir/pqc"
    classic_cert_dir="$keys_dir/classic"
    hybrid_cert_dir="$keys_dir/hybrid"

    # Set the alg-list txt filepaths
    sig_alg_file="$test_data_dir/alg_lists/tls_sig_algs.txt"
    hybrid_sig_alg_file="$test_data_dir/alg_lists/tls_hybr_sig_algs.txt"

    # Create the PQC and Hybrid-PQC digital signature algorithm list arrays
    sig_algs=()
    while IFS= read -r line; do
        sig_algs+=("$line")
    done < $sig_alg_file

    hybrid_sig_algs=()
    while IFS= read -r line; do
        hybrid_sig_algs+=("$line")
    done < $hybrid_sig_alg_file

    # Declaring classic digital signature algorithms array
    classic_sigs=( "RSA:2048" "RSA:3072" "RSA:4096" "prime256v1" "secp384r1" "secp521r1")

}

#-------------------------------------------------------------------------------------------------------------------------------

function classic_keygen() {
    # Function for generating cross-signed certificate chains for Classic TLS (RSA/ECC).
    # Scenario 3:
    #   RootA (untrusted) → IntermediateA → Server
    #   RootB (trusted by client) cross-signs RootA.
    #   Client Truststore = RootB.crt
    #   Server sends: srv.crt + IntermediateA.crt + RootA_cross_by_RootB.crt

    for sig in "${classic_sigs[@]}"; do

        # Sanitize the algorithm name for filenames
        sig_name="${sig//[:\/]/_}"

        echo "[INFO] Generating cross-signed classic chain for $sig_name"

        # ========== RSA CHAIN GENERATION ==========
        if [[ $sig == RSA:* ]]; then
            key_bits="${sig#RSA:}"
            keygen_cmd="-newkey rsa:${key_bits}"

            # === 1. Root A (untrusted CA) ===
            "$openssl_path/bin/openssl" req -new -nodes $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_RootA.key" \
                -out "$classic_cert_dir/${sig_name}_RootA.csr" \
                -subj "/CN=RootA $sig CA" \
                -config "$openssl_path/openssl.cnf" || {
                echo "[ERROR] Failed to create RootA CSR for $sig_name"
                continue
            }

            # Self-sign RootA
            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_RootA.csr" \
                -signkey "$classic_cert_dir/${sig_name}_RootA.key" \
                -out "$classic_cert_dir/${sig_name}_RootA.crt" \
                -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_ca  || {
                echo "[ERROR] Failed to self-sign RootA for $sig_name"
                continue
            }

            # === 2. Root B (trusted CA) ===
            "$openssl_path/bin/openssl" req -x509 -new $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_RootB.key" \
                -out "$classic_cert_dir/${sig_name}_RootB.crt" \
                -nodes -subj "/CN=RootB $sig CA" -days 365 \
                -config "$openssl_path/openssl.cnf" -extensions v3_ca || {
                echo "[ERROR] Failed to create RootB for $sig_name"
                continue
            }

            # === 3. RootB cross-signs RootA CSR ===
            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_RootA.csr" \
                -out "$classic_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
                -CA "$classic_cert_dir/${sig_name}_RootB.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_RootB.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca || {
                echo "[ERROR] Failed to cross-sign RootA by RootB for $sig_name"
                continue
            }

            rm -f "$classic_cert_dir/${sig_name}_RootA.csr"

            # === 4. IntermediateA signed by RootA ===
            "$openssl_path/bin/openssl" req -new -nodes $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_IntermediateA.key" \
                -out "$classic_cert_dir/${sig_name}_IntermediateA.csr" \
                -subj "/CN=IntermediateA $sig" \
                -config "$openssl_path/openssl.cnf"

            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_IntermediateA.csr" \
                -out "$classic_cert_dir/${sig_name}_IntermediateA.crt" \
                -CA "$classic_cert_dir/${sig_name}_RootA.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_RootA.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca

            rm -f "$classic_cert_dir/${sig_name}_IntermediateA.csr"

            # === 5. Server certificate signed by IntermediateA ===
            "$openssl_path/bin/openssl" req -new -nodes $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_srv.key" \
                -out "$classic_cert_dir/${sig_name}_srv.csr" \
                -subj "/CN=Server $sig" \
                -config "$openssl_path/openssl.cnf"

            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_srv.csr" \
                -out "$classic_cert_dir/${sig_name}_srv.crt" \
                -CA "$classic_cert_dir/${sig_name}_IntermediateA.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_IntermediateA.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions server_cert

            rm -f "$classic_cert_dir/${sig_name}_srv.csr"

        # ========== ECC CHAIN GENERATION ==========
        else
            ecc_curve="$sig"

            # === 1. Root A (untrusted CA) ===
            "$openssl_path/bin/openssl" ecparam -name "$ecc_curve" -genkey \
                -out "$classic_cert_dir/${sig_name}_RootA.key" || {
                echo "[ERROR] Failed to generate RootA key for $sig_name"
                continue
            }

            "$openssl_path/bin/openssl" req -new \
                -key "$classic_cert_dir/${sig_name}_RootA.key" \
                -out "$classic_cert_dir/${sig_name}_RootA.csr" \
                -subj "/CN=RootA $sig CA" \
                -config "$openssl_path/openssl.cnf" || {
                echo "[ERROR] Failed to create RootA CSR for $sig_name"
                continue
            }

            # Self-sign RootA
            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_RootA.csr" \
                -signkey "$classic_cert_dir/${sig_name}_RootA.key" \
                -out "$classic_cert_dir/${sig_name}_RootA.crt" \
                -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_ca  || {
                echo "[ERROR] Failed to self-sign RootA for $sig_name"
                continue
            }

            # === 2. Root B (trusted CA) ===
            "$openssl_path/bin/openssl" ecparam -name "$ecc_curve" -genkey \
                -out "$classic_cert_dir/${sig_name}_RootB.key" || {
                echo "[ERROR] Failed to generate RootB key for $sig_name"
                continue
            }

            "$openssl_path/bin/openssl" req -x509 -new \
                -key "$classic_cert_dir/${sig_name}_RootB.key" \
                -out "$classic_cert_dir/${sig_name}_RootB.crt" \
                -subj "/CN=RootB $sig CA" -days 365 \
                -config "$openssl_path/openssl.cnf"  -extensions v3_ca || {
                echo "[ERROR] Failed to create RootB for $sig_name"
                continue
            }

            # === 3. RootB cross-signs RootA CSR ===
            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_RootA.csr" \
                -out "$classic_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
                -CA "$classic_cert_dir/${sig_name}_RootB.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_RootB.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca || {
                echo "[ERROR] Failed to cross-sign RootA by RootB for $sig_name"
                continue
            }

            rm -f "$classic_cert_dir/${sig_name}_RootA.csr"

            # === 4. IntermediateA signed by RootA ===
            "$openssl_path/bin/openssl" ecparam -name "$ecc_curve" -genkey \
                -out "$classic_cert_dir/${sig_name}_IntermediateA.key"

            "$openssl_path/bin/openssl" req -new \
                -key "$classic_cert_dir/${sig_name}_IntermediateA.key" \
                -out "$classic_cert_dir/${sig_name}_IntermediateA.csr" \
                -subj "/CN=IntermediateA $sig" \
                -config "$openssl_path/openssl.cnf"

            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_IntermediateA.csr" \
                -out "$classic_cert_dir/${sig_name}_IntermediateA.crt" \
                -CA "$classic_cert_dir/${sig_name}_RootA.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_RootA.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca

            rm -f "$classic_cert_dir/${sig_name}_IntermediateA.csr"

            # === 5. Server certificate signed by IntermediateA ===
            "$openssl_path/bin/openssl" ecparam -name "$ecc_curve" -genkey \
                -out "$classic_cert_dir/${sig_name}_srv.key"

            "$openssl_path/bin/openssl" req -new \
                -key "$classic_cert_dir/${sig_name}_srv.key" \
                -out "$classic_cert_dir/${sig_name}_srv.csr" \
                -subj "/CN=Server $sig" \
                -config "$openssl_path/openssl.cnf"

            "$openssl_path/bin/openssl" x509 -req \
                -in "$classic_cert_dir/${sig_name}_srv.csr" \
                -out "$classic_cert_dir/${sig_name}_srv.crt" \
                -CA "$classic_cert_dir/${sig_name}_IntermediateA.crt" \
                -CAkey "$classic_cert_dir/${sig_name}_IntermediateA.key" \
                -CAcreateserial -days 365 \
                -extfile "$openssl_path/openssl.cnf" -extensions server_cert

            rm -f "$classic_cert_dir/${sig_name}_srv.csr"
        fi

        # === 6. Build full server chain (common for both RSA and ECC) ===
        if [ ! -f "$classic_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" ]; then
            echo "[ERROR] Cross-signed certificate missing for $sig_name"
            continue
        fi

        cat \
            "$classic_cert_dir/${sig_name}_srv.crt" \
            "$classic_cert_dir/${sig_name}_IntermediateA.crt" \
            "$classic_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
            > "$classic_cert_dir/${sig_name}_server_chain.crt"

        echo "[OK]  Chain ready: ${sig_name}_server_chain.crt"
        echo "     Client trust anchor: ${sig_name}_RootB.crt"
    done
}

# PQC function remains the same
function pqc_keygen() {
    # Function for generating cross-signed PQC certificate chains for TLS benchmarking.
    # Scenario:
    #  - RootA (not trusted by client)
    #  - RootB (trusted by client)
    #  - RootA is cross-signed by RootB
    #  - IntermediateA is issued by RootA
    #  - Server is issued by IntermediateA
    #  => Server sends: srv.crt + IntermediateA.crt + RootA_cross_by_RootB.crt
    #  => Client trusts only RootB.crt

    for sig in "${sig_algs[@]}"; do
        sig_name="${sig//[:\/]/_}"

        echo "[INFO] Generating PQC cross-signed chain for $sig_name"

        # === 1. Root A (untrusted) ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$pqc_cert_dir/${sig_name}_RootA.key" \
            -out "$pqc_cert_dir/${sig_name}_RootA.csr" \
            -subj "/CN=RootA $sig CA" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to create RootA CSR for $sig_name"
            continue
        }

        # Self-sign RootA
        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig_name}_RootA.csr" \
            -signkey "$pqc_cert_dir/${sig_name}_RootA.key" \
            -out "$pqc_cert_dir/${sig_name}_RootA.crt" \
            -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions v3_ca \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to self-sign RootA for $sig_name"
            continue
        }

        # === 2. Root B (trusted) ===
        "$openssl_path/bin/openssl" req -x509 -new -newkey "$sig" -nodes \
            -keyout "$pqc_cert_dir/${sig_name}_RootB.key" \
            -out "$pqc_cert_dir/${sig_name}_RootB.crt" \
            -subj "/CN=RootB $sig CA" -days 365 \
            -config "$openssl_path/openssl.cnf" \
            -config "$openssl_path/openssl.cnf" -extensions v3_ca \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to create RootB for $sig_name"
            continue
        }

        # === 3. RootB cross-signs RootA CSR ===
        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig_name}_RootA.csr" \
            -out "$pqc_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
            -CA "$pqc_cert_dir/${sig_name}_RootB.crt" \
            -CAkey "$pqc_cert_dir/${sig_name}_RootB.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path" \
            -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca || {
            echo "[ERROR] Failed to cross-sign RootA by RootB for $sig_name"
            continue
        }

        rm -f "$pqc_cert_dir/${sig_name}_RootA.csr"

        # === 4. IntermediateA signed by RootA ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$pqc_cert_dir/${sig_name}_IntermediateA.key" \
            -out "$pqc_cert_dir/${sig_name}_IntermediateA.csr" \
            -subj "/CN=IntermediateA $sig" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig_name}_IntermediateA.csr" \
            -out "$pqc_cert_dir/${sig_name}_IntermediateA.crt" \
            -CA "$pqc_cert_dir/${sig_name}_RootA.crt" \
            -CAkey "$pqc_cert_dir/${sig_name}_RootA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$pqc_cert_dir/${sig_name}_IntermediateA.csr"

        # === 5. Server signed by IntermediateA ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$pqc_cert_dir/${sig_name}_srv.key" \
            -out "$pqc_cert_dir/${sig_name}_srv.csr" \
            -subj "/CN=Server $sig" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig_name}_srv.csr" \
            -out "$pqc_cert_dir/${sig_name}_srv.crt" \
            -CA "$pqc_cert_dir/${sig_name}_IntermediateA.crt" \
            -CAkey "$pqc_cert_dir/${sig_name}_IntermediateA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions server_cert \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$pqc_cert_dir/${sig_name}_srv.csr"

        # === 6. Build server chain ===
        if [ ! -f "$pqc_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" ]; then
            echo "[ERROR] Cross-signed certificate missing for $sig_name"
            continue
        fi

        cat \
            "$pqc_cert_dir/${sig_name}_srv.crt" \
            "$pqc_cert_dir/${sig_name}_IntermediateA.crt" \
            "$pqc_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
            > "$pqc_cert_dir/${sig_name}_server_chain.crt"

        echo "[OK]  Chain ready: ${sig_name}_server_chain.crt"
        echo "     Client trust anchor: ${sig_name}_RootB.crt"
    done
}

function hybrid_pqc_keygen() {
    # Function for generating cross-signed Hybrid-PQC certificate chains for TLS benchmarking.
    # Scenario:
    #  - RootA (not trusted by client)
    #  - RootB (trusted by client)
    #  - RootA is cross-signed by RootB
    #  - IntermediateA is issued by RootA
    #  - Server is issued by IntermediateA
    #  => Server sends: srv.crt + IntermediateA.crt + RootA_cross_by_RootB.crt
    #  => Client trusts only RootB.crt

    for sig in "${hybrid_sig_algs[@]}"; do
        sig_name="${sig//[:\/]/_}"

        echo "[INFO] Generating Hybrid-PQC cross-signed chain for $sig_name"

        # === 1. Root A (untrusted) ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$hybrid_cert_dir/${sig_name}_RootA.key" \
            -out "$hybrid_cert_dir/${sig_name}_RootA.csr" \
            -subj "/CN=RootA $sig Hybrid CA" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to create RootA CSR for $sig_name"
            continue
        }

        # Self-sign RootA
        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig_name}_RootA.csr" \
            -signkey "$hybrid_cert_dir/${sig_name}_RootA.key" \
            -out "$hybrid_cert_dir/${sig_name}_RootA.crt" \
            -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to self-sign RootA for $sig_name"
            continue
        }

        # === 2. Root B (trusted) ===
        "$openssl_path/bin/openssl" req -x509 -new -newkey "$sig" -nodes \
            -keyout "$hybrid_cert_dir/${sig_name}_RootB.key" \
            -out "$hybrid_cert_dir/${sig_name}_RootB.crt" \
            -subj "/CN=RootB $sig Hybrid CA" -days 365 \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to create RootB for $sig_name"
            continue
        }

        # === 3. RootB cross-signs RootA ===
        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig_name}_RootA.csr" \
            -out "$hybrid_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
            -CA "$hybrid_cert_dir/${sig_name}_RootB.crt" \
            -CAkey "$hybrid_cert_dir/${sig_name}_RootB.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path" || {
            echo "[ERROR] Failed to cross-sign RootA by RootB for $sig_name"
            continue
        }

        rm -f "$hybrid_cert_dir/${sig_name}_RootA.csr"

        # === 4. IntermediateA signed by RootA ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$hybrid_cert_dir/${sig_name}_IntermediateA.key" \
            -out "$hybrid_cert_dir/${sig_name}_IntermediateA.csr" \
            -subj "/CN=IntermediateA $sig Hybrid" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig_name}_IntermediateA.csr" \
            -out "$hybrid_cert_dir/${sig_name}_IntermediateA.crt" \
            -CA "$hybrid_cert_dir/${sig_name}_RootA.crt" \
            -CAkey "$hybrid_cert_dir/${sig_name}_RootA.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$hybrid_cert_dir/${sig_name}_IntermediateA.csr"

        # === 5. Server signed by IntermediateA ===
        "$openssl_path/bin/openssl" req -new -newkey "$sig" -nodes \
            -keyout "$hybrid_cert_dir/${sig_name}_srv.key" \
            -out "$hybrid_cert_dir/${sig_name}_srv.csr" \
            -subj "/CN=Server $sig Hybrid" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig_name}_srv.csr" \
            -out "$hybrid_cert_dir/${sig_name}_srv.crt" \
            -CA "$hybrid_cert_dir/${sig_name}_IntermediateA.crt" \
            -CAkey "$hybrid_cert_dir/${sig_name}_IntermediateA.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$hybrid_cert_dir/${sig_name}_srv.csr"

        # === 6. Build full chain ===
        if [ ! -f "$hybrid_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" ]; then
            echo "[ERROR] Cross-signed certificate missing for $sig_name"
            continue
        fi

        cat \
            "$hybrid_cert_dir/${sig_name}_srv.crt" \
            "$hybrid_cert_dir/${sig_name}_IntermediateA.crt" \
            "$hybrid_cert_dir/${sig_name}_RootA_cross_by_RootB.crt" \
            > "$hybrid_cert_dir/${sig_name}_server_chain.crt"

        echo "[OK]  Chain ready: ${sig_name}_server_chain.crt"
        echo "     Client trust anchor: ${sig_name}_RootB.crt"
    done
}

#-------------------------------------------------------------------------------------------------------------------------------
function main() {
    # Main function coordinating the generation of certificates and private keys for TLS handshake benchmarking tests.
    # This includes support for classic, post-quantum (PQC), and Hybrid-PQC digital signature algorithms.

    # Output the welcome message to the terminal
    echo "#########################################################"
    echo "PQC-LEO - TLS Certificate & Key Generator"
    echo "Classic | PQC | Hybrid-PQC (OpenSSL 3.5.0 + OQS-Provider)"
    echo -e "#########################################################\n"

    # Setup the base environment for the script
    setup_base_env

    # Modify the OpenSSL conf file to temporarily remove the default groups configuration
    if ! "$util_scripts/configure_openssl_cnf.sh" 1; then
        echo "[ERROR] - Failed to modify OpenSSL configuration."
        exit 1
    fi

    # Remove the old keys if present and create the key storage directories
    if [ -d "$keys_dir" ]; then
        rm -rf "$keys_dir"
    fi
    mkdir -p "$pqc_cert_dir" && mkdir -p "$classic_cert_dir" && mkdir -p "$hybrid_cert_dir"

    # Generate the certs and keys for the classic ciphersuite tests
    echo -e "\nGenerating certs and keys for classic ciphersuite tests:"
    classic_keygen

    # Generate the certs and keys for the PQC tests
    echo -e "\nGenerating certs and keys for PQC tests:"
    pqc_keygen

    # Generate the certs and keys for the Hybrid-PQC tests
    echo -e "\nGenerating certs and keys for Hybrid-PQC tests:"
    hybrid_pqc_keygen

    # Restore the OpenSSL conf file to have the configuration needed for testing scripts
    if ! "$util_scripts/configure_openssl_cnf.sh" 2; then
        echo "[ERROR] - Failed to modify OpenSSL configuration."
        exit 1
    fi

}
main