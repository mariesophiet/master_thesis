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

    # Continue moving up the directory tree until the .pqc_eval_dir_marker.tmp file is found
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
    # Function for generating standard Classic TLS certificate chains (RSA/ECC)
    # Scenario 2: Root -> Intermediate -> Server
    # Client Truststore = Root.crt
    # Server sends: srv.crt + intCA.crt

    for sig in "${classic_sigs[@]}"; do
        if [[ $sig == RSA:* ]]; then
            sig_name="${sig/:/_}"
            keygen_cmd="-newkey rsa:${sig#RSA:}"
        else
            sig_name=$sig
            keygen_cmd=""
        fi

        echo "[INFO] - Generating certificate chain for $sig"

        # === 1. Root CA ===
        if [[ $sig == RSA:* ]]; then
            "$openssl_path/bin/openssl" req -x509 -new $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_rootCA.key" \
                -out "$classic_cert_dir/${sig_name}_rootCA.crt" \
                -nodes -subj "/CN=oqstest Root CA" -days 365 \
                -config "$openssl_path/openssl.cnf" -extensions v3_ca
        else
            "$openssl_path/bin/openssl" ecparam -name $sig -genkey \
                -out "$classic_cert_dir/${sig_name}_rootCA.key"
            "$openssl_path/bin/openssl" req -x509 -new \
                -key "$classic_cert_dir/${sig_name}_rootCA.key" \
                -out "$classic_cert_dir/${sig_name}_rootCA.crt" \
                -subj "/CN=oqstest Root CA" -days 365 \
                -config "$openssl_path/openssl.cnf" -extensions v3_ca
        fi

        # === 2. Intermediate CA ===
        if [[ $sig == RSA:* ]]; then
            "$openssl_path/bin/openssl" req -new $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_intCA.key" \
                -out "$classic_cert_dir/${sig_name}_intCA.csr" \
                -nodes -subj "/CN=oqstest Intermediate CA" \
                -config "$openssl_path/openssl.cnf"
        else
            "$openssl_path/bin/openssl" ecparam -name $sig -genkey \
                -out "$classic_cert_dir/${sig_name}_intCA.key"
            "$openssl_path/bin/openssl" req -new \
                -key "$classic_cert_dir/${sig_name}_intCA.key" \
                -out "$classic_cert_dir/${sig_name}_intCA.csr" \
                -subj "/CN=oqstest Intermediate CA" \
                -config "$openssl_path/openssl.cnf"
        fi

        "$openssl_path/bin/openssl" x509 -req \
            -in "$classic_cert_dir/${sig_name}_intCA.csr" \
            -out "$classic_cert_dir/${sig_name}_intCA.crt" \
            -CA "$classic_cert_dir/${sig_name}_rootCA.crt" \
            -CAkey "$classic_cert_dir/${sig_name}_rootCA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca 

        rm -f "$classic_cert_dir/${sig_name}_intCA.csr"

        # === 3. Server certificate ===
        if [[ $sig == RSA:* ]]; then
            "$openssl_path/bin/openssl" req -new $keygen_cmd \
                -keyout "$classic_cert_dir/${sig_name}_srv.key" \
                -out "$classic_cert_dir/${sig_name}_srv.csr" \
                -nodes -subj "/CN=oqstest server" \
                -config "$openssl_path/openssl.cnf"
        else
            "$openssl_path/bin/openssl" ecparam -name $sig -genkey \
                -out "$classic_cert_dir/${sig_name}_srv.key"
            "$openssl_path/bin/openssl" req -new \
                -key "$classic_cert_dir/${sig_name}_srv.key" \
                -out "$classic_cert_dir/${sig_name}_srv.csr" \
                -subj "/CN=oqstest server" \
                -config "$openssl_path/openssl.cnf"
        fi

        "$openssl_path/bin/openssl" x509 -req \
            -in "$classic_cert_dir/${sig_name}_srv.csr" \
            -out "$classic_cert_dir/${sig_name}_srv.crt" \
            -CA "$classic_cert_dir/${sig_name}_intCA.crt" \
            -CAkey "$classic_cert_dir/${sig_name}_intCA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions server_cert \

        rm -f "$classic_cert_dir/${sig_name}_srv.csr"

        # === 4. Build combined chain for server ===
        cat "$classic_cert_dir/${sig_name}_srv.crt" \
            "$classic_cert_dir/${sig_name}_intCA.crt" > "$classic_cert_dir/${sig_name}_srv_chain.crt"

        echo "[INFO] - Chain ready: ${sig_name}_srv_chain.crt (srv + intCA)"
        echo "[INFO] - Client Truststore should contain: ${sig_name}_rootCA.crt"

    done

}

#-------------------------------------------------------------------------------------------------------------------------------
function pqc_keygen() {
    # Function for generating standard (non-cross-signed) PQC certificate chains.
    # Scenario 2: Root -> Intermediate -> Server
    # Client Truststore = Root.crt
    # Server sends: srv.crt + intCA.crt

    for sig in "${sig_algs[@]}"; do
        echo "[INFO] - Generating certificate chain for $sig"

        # --- 1. Root CA ---
        "$openssl_path/bin/openssl" req -x509 -new -newkey $sig \
            -keyout "$pqc_cert_dir/${sig}_rootCA.key" \
            -out "$pqc_cert_dir/${sig}_rootCA.crt" \
            -nodes -subj "/CN=oqstest $sig Root CA" -days 365 \
            -config "$openssl_path/openssl.cnf"  -extensions v3_ca \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        # --- 2. Intermediate CA ---
        "$openssl_path/bin/openssl" req -new -newkey $sig \
            -keyout "$pqc_cert_dir/${sig}_intCA.key" \
            -out "$pqc_cert_dir/${sig}_intCA.csr" \
            -nodes -subj "/CN=oqstest $sig Intermediate CA" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig}_intCA.csr" \
            -out "$pqc_cert_dir/${sig}_intCA.crt" \
            -CA "$pqc_cert_dir/${sig}_rootCA.crt" \
            -CAkey "$pqc_cert_dir/${sig}_rootCA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions v3_intermediate_ca \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$pqc_cert_dir/${sig}_intCA.csr"

        # --- 3. Server certificate ---
        "$openssl_path/bin/openssl" req -new -newkey $sig \
            -keyout "$pqc_cert_dir/${sig}_srv.key" \
            -out "$pqc_cert_dir/${sig}_srv.csr" \
            -nodes -subj "/CN=oqstest $sig server" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$pqc_cert_dir/${sig}_srv.csr" \
            -out "$pqc_cert_dir/${sig}_srv.crt" \
            -CA "$pqc_cert_dir/${sig}_intCA.crt" \
            -CAkey "$pqc_cert_dir/${sig}_intCA.key" \
            -CAcreateserial -days 365 \
            -extfile "$openssl_path/openssl.cnf" -extensions server_cert \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$pqc_cert_dir/${sig}_srv.csr"

        # --- 4. Build combined chain for the server ---
        cat "$pqc_cert_dir/${sig}_srv.crt" \
            "$pqc_cert_dir/${sig}_intCA.crt" > "$pqc_cert_dir/${sig}_srv_chain.crt"

        echo "[INFO] - Chain ready: ${sig}_srv_chain.crt (srv + intCA)"
        echo "[INFO] - Client Truststore should contain: ${sig}_rootCA.crt"

    done

}

#-------------------------------------------------------------------------------------------------------------------------------
function hybrid_pqc_keygen() {
    # Function for generating standard Hybrid-PQC certificate chains.
    # Scenario 2: Root -> Intermediate -> Server
    # Client Truststore = Root.crt
    # Server sends: srv.crt + intCA.crt

    for sig in "${hybrid_sig_algs[@]}"; do
        echo "[INFO] - Generating certificate chain for Hybrid-PQC algorithm: $sig"

        # --- 1. Root CA ---
        "$openssl_path/bin/openssl" req -x509 -new -newkey $sig \
            -keyout "$hybrid_cert_dir/${sig}_rootCA.key" \
            -out "$hybrid_cert_dir/${sig}_rootCA.crt" \
            -nodes -subj "/CN=oqstest $sig Root CA" -days 365 \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        # --- 2. Intermediate CA ---
        "$openssl_path/bin/openssl" req -new -newkey $sig \
            -keyout "$hybrid_cert_dir/${sig}_intCA.key" \
            -out "$hybrid_cert_dir/${sig}_intCA.csr" \
            -nodes -subj "/CN=oqstest $sig Intermediate CA" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig}_intCA.csr" \
            -out "$hybrid_cert_dir/${sig}_intCA.crt" \
            -CA "$hybrid_cert_dir/${sig}_rootCA.crt" \
            -CAkey "$hybrid_cert_dir/${sig}_rootCA.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$hybrid_cert_dir/${sig}_intCA.csr"

        # --- 3. Server certificate ---
        "$openssl_path/bin/openssl" req -new -newkey $sig \
            -keyout "$hybrid_cert_dir/${sig}_srv.key" \
            -out "$hybrid_cert_dir/${sig}_srv.csr" \
            -nodes -subj "/CN=oqstest $sig server" \
            -config "$openssl_path/openssl.cnf" \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        "$openssl_path/bin/openssl" x509 -req \
            -in "$hybrid_cert_dir/${sig}_srv.csr" \
            -out "$hybrid_cert_dir/${sig}_srv.crt" \
            -CA "$hybrid_cert_dir/${sig}_intCA.crt" \
            -CAkey "$hybrid_cert_dir/${sig}_intCA.key" \
            -CAcreateserial -days 365 \
            -provider default -provider oqsprovider -provider-path "$provider_path"

        rm -f "$hybrid_cert_dir/${sig}_srv.csr"

        # --- 4. Build combined chain for the server ---
        cat "$hybrid_cert_dir/${sig}_srv.crt" \
            "$hybrid_cert_dir/${sig}_intCA.crt" > "$hybrid_cert_dir/${sig}_srv_chain.crt"

        echo "[INFO] - Chain ready: ${sig}_srv_chain.crt (srv + intCA)"
        echo "[INFO] - Client Truststore should contain: ${sig}_rootCA.crt"

    done

}

#-------------------------------------------------------------------------------------------------------------------------------
function main() {
    # Main function coordinating the generation of certificates and private keys for TLS handshake benchmarking tests.
    # This includes support for classic, post-quantum (PQC), and Hybrid-PQC digital signature algorithms.

    # Output the welcome message to the terminal
    echo "#########################################################"
    echo "PQC-Evaluation-Tools - TLS Certificate & Key Generator"
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