#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import os
import logging
import json
from os import getenv
from minio import Minio
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def minio_login(server: str, port: int, access_key: str, secret_key: str) -> Minio:
    """
    Establish a connection to the MinIO server

    Args:
        server (str)    : The hostname or IP address of the MinIO server.
        port (int)      : The port number used for API calls to the MinIO server.
        access_key (str): The access key used to authenticate with the MinIO server.
        secret_key (str): The secret key used to authenticate with the MinIO server.

    Returns:
        Minio: A MinIO client instance that can be used to interact with the server.
    """
    client = Minio(
        f"{server}:{port}",
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )

    return client


def create_bucket(client: Minio, bucket: str) -> None:
    """
    Create one or more buckets on the MinIO server.

    Args:
        client (Minio)  : The Minio connection instance
        bucket (str)    : The name of the bucket to create.

    Returns:
        None: This function does not return anything
    """
    # Initialize the MinIO client
    client = client

    # Check if the specified bucket exists, if not create it.
    if client.bucket_exists(bucket):
        logging.info(f"Bucket '{bucket}' exists.")
    else:
        # Create the bucket
        logging.info(f"Creating bucket: {bucket}")
        client.make_bucket(bucket)


if __name__ == '__main__':
    # =================================================================
    # Establish a connection to the MinIO Server, using least privilege
    # =================================================================
    minio_server = getenv("MINIO_SERVER")
    minio_port = getenv("MINIO_PORT")
    minio_secure = getenv("MINIO_SECURE")
    bucketcreator_access_key = getenv("BUCKET_CREATOR_ACCESS_KEY")
    bucketcreator_secret_key = getenv("BUCKET_CREATOR_SECRET_KEY")

    # Get the list of buckets to create
    script_dir = os.path.dirname(__file__)
    bucket_config_file = os.path.join(script_dir, '..', 'config', 'minio_buckets.json')

    # Get Some DEBUG info
    logging.info(f"MINIO_SERVER = {minio_server}")
    logging.info(f"MINIO_PORT = {minio_port}")
    logging.info(f"MINIO_SECURE = {minio_secure}")

    # Create a connection instance using the bucketcreator API bucketcreator credentials
    conn = minio_login(minio_server,
                       minio_port,
                       bucketcreator_access_key,
                       bucketcreator_secret_key
                       )

    # Now lets create our buckets
    try:
        with open(bucket_config_file, 'r') as f:
            data = json.load(f)
            buckets = data.get('buckets', [])

            if buckets:
                print("MinIO Bucket Names:")
                for bucket_name in buckets:
                    create_bucket(conn, bucket_name)
            else:
                print("No buckets found in JSON file")

    except FileNotFoundError:
        logging.error(f"The file {bucket_config_file} was not found.")
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from {bucket_config_file}.")
    except Exception as e:
        logging.info(f"An unexpected error was encountered {e}")
