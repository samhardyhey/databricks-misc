#!/usr/bin/env python3
"""
HPS Clinical Notes Interactive Clusters Management Script

This script manages interactive clusters with JSL libraries using the Databricks SDK.
Databricks Asset Bundles don't support 'libraries' field for interactive clusters as of Feb 2026,
so this script provides an alternative approach using the Python SDK.

Usage:
    python manage_clusters.py create --target prod-sp --profile prod-sp
    python manage_clusters.py delete --target prod-sp --profile prod-sp
    python manage_clusters.py status --target prod-sp --profile prod-sp
    python manage_clusters.py install-libraries --cluster-name hps-clinical-notes-interactive-dbr1 --profile prod-sp

Notes:
    - JSL secrets are automatically injected using {{secrets/...}} syntax
    - Libraries are automatically installed after cluster creation
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import DataSecurityMode, RuntimeEngine, ClusterSpec
from databricks.sdk.service.compute import Library, ClusterAccessControlRequest, ClusterPermissionLevel
from databricks.sdk.service.compute import PythonPyPiLibrary


def load_cluster_configs() -> Dict[str, Dict]:
    """Load cluster configurations from the DAB variables and resources."""
    
    # Base configuration matching the DAB YAML structure
    base_config = {
        "spark_version": "16.4.x-cpu-ml-scala2.12",
        "node_type_id": "Standard_E16_v3",
        "num_workers": 0,
        "data_security_mode": DataSecurityMode.SINGLE_USER,
        "runtime_engine": RuntimeEngine.STANDARD,
        "autotermination_minutes": 60,
        "spark_conf": {
            # Required single node cluster configuration
            "spark.databricks.cluster.profile": "singleNode",
            "spark.master": "local[*]",
            # JSL-specific configurations
            "spark.sql.legacy.allowUntypedScalaUDF": "true",
            "spark.databricks.unityCatalog.volumes.enabled": "true",
            "spark.rpc.message.maxSize": "1024",
            # Enhanced JVM garbage collection optimization
            "spark.driver.extraJavaOptions": "-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+AlwaysPreTouch -XX:G1HeapRegionSize=32M",
            "spark.executor.extraJavaOptions": "-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+AlwaysPreTouch -XX:G1HeapRegionSize=32M",
            # Spark performance optimization
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            # Memory configurations
            "spark.driver.memory": "32g",
            "spark.driver.memoryOverhead": "32g",
            "spark.memory.offHeap.enabled": "true",
            "spark.memory.offHeap.size": "10g",
            "spark.kryoserializer.buffer.max": "2000M",
            "spark.driver.maxResultSize": "4g",
            "spark.executor.memory": "2g",
            # Additional optimizations for JSL workloads
            "spark.sql.adaptive.advisoryPartitionSizeInBytes": "128MB",
            "spark.sql.adaptive.skewJoin.enabled": "true",
            "spark.dynamicAllocation.enabled": "false",
        },
        "custom_tags": {
            "stage": "Discover",
            "business_unit": "HPS",
            "division": "Healthcare",
            "workspace": "HPS Clinical Notes",
            "ResourceClass": "SingleNode",
            "cluster_type": "Interactive",
            "cluster_purpose": "Development",
        }
    }
    
    return {
        "dbr1": {
            **base_config,
            "cluster_name_template": "hps-clinical-notes-interactive-dbr1",
            "spark_env_vars_template": {
                "SPARK_NLP_LICENSE": "{{secrets/prod_ml_secret_scope/10801-spark-nlp-license}}",
                "SPARK_OCR_LICENSE": "{{secrets/prod_ml_secret_scope/10801-spark-ocr-license}}",
                "AWS_ACCESS_KEY_ID": "{{secrets/prod_ml_secret_scope/10801-aws-access-key-id}}",
                "AWS_SECRET_ACCESS_KEY": "{{secrets/prod_ml_secret_scope/10801-aws-secret-access-key}}",
            },
            "autotermination_minutes": 60,
        },
        "dbr2": {
            **base_config,
            "cluster_name_template": "hps-clinical-notes-interactive-dbr2",
            "spark_env_vars_template": {
                "SPARK_NLP_LICENSE": "{{secrets/prod_ml_secret_scope/10800-spark-nlp-license}}",
                "SPARK_OCR_LICENSE": "{{secrets/prod_ml_secret_scope/10800-spark-ocr-license}}",
                "AWS_ACCESS_KEY_ID": "{{secrets/prod_ml_secret_scope/10800-aws-access-key-id}}",
                "AWS_SECRET_ACCESS_KEY": "{{secrets/prod_ml_secret_scope/10800-aws-secret-access-key}}",
            },
            "autotermination_minutes": 60,
        }
    }


def get_target_schema(target: str) -> str:
    """Get the schema name for the given target."""
    if target == "prod-sp":
        return "prod"
    elif target == "dev-sp":
        return "dev"
    else:
        raise ValueError(f"Unknown target: {target}")


def set_cluster_permissions(client: WorkspaceClient, cluster_id: str) -> None:
    """Set cluster permissions for user, service principal, and AD groups."""
    try:
        # Define access control list with manage permissions (includes attach)
        access_control_list = [
            # Individual user permissions - can manage
            ClusterAccessControlRequest(
                user_name="sam.hardy@ebosgroup.com",
                permission_level=ClusterPermissionLevel.CAN_MANAGE
            ),
            # AD Group permissions for ML AI team - can manage
            ClusterAccessControlRequest(
                group_name="HPS_Clinical_Notes_Discover_MLAI_Group",
                permission_level=ClusterPermissionLevel.CAN_MANAGE
            ),
            # AD Group permissions for JSL team - can manage
            ClusterAccessControlRequest(
                group_name="HPS_Clinical_Notes_Discover_JSL_Group",
                permission_level=ClusterPermissionLevel.CAN_MANAGE
            ),
            # AD Group permissions for CRUD team - can manage
            ClusterAccessControlRequest(
                group_name="HPS_Clinical_Notes_Discover_CRUD_Group",
                permission_level=ClusterPermissionLevel.CAN_MANAGE
            ),
            # Note: Service principal permissions may need workspace admin setup
            # ClusterAccessControlRequest(
            #     service_principal_name="09e33a82-ba3a-4f11-a5d8-ede6e3b6bd35",  # HPS ML Service Principal
            #     permission_level=ClusterPermissionLevel.CAN_MANAGE
            # )
        ]
        
        client.clusters.set_permissions(
            cluster_id=cluster_id,
            access_control_list=access_control_list
        )
        print(f"    ✓ Set cluster permissions for user and AD groups (manage)")
        
    except Exception as e:
        print(f"    ✗ Failed to set cluster permissions: {e}")


def get_jsl_libraries() -> List[Library]:
    """Get the list of JSL libraries to install."""
    return [
        # Python wheel libraries from workspace and volumes
        Library(whl="/Workspace/HPS_Clinical_Notes_Discover/JSL/spark_ocr-6.2.0rc1-py3-none-any.whl"),
        Library(whl="/Volumes/hps_clinical_notes_discover/custom/libraries/spark_nlp_jsl-6.3.0-py3-none-any.whl"),
        
        # JAR libraries from volumes
        Library(jar="/Volumes/hps_clinical_notes_discover/custom/libraries/spark-nlp-assembly-6.3.1.jar"),
        Library(jar="/Volumes/hps_clinical_notes_discover/custom/libraries/spark-ocr-assembly-6.3.0.jar"),
        Library(jar="/Volumes/hps_clinical_notes_discover/custom/libraries/spark-nlp-jsl-6.3.0.jar"),
        
        # Required Python packages with specific versions
        Library(pypi=PythonPyPiLibrary(package="spark-nlp==6.3.1")),
        Library(pypi=PythonPyPiLibrary(package="pandas==1.5.3")),
        Library(pypi=PythonPyPiLibrary(package="numpy==1.26.4")),
        Library(pypi=PythonPyPiLibrary(package="openpyxl==3.1.5")),
        Library(pypi=PythonPyPiLibrary(package="RapidFuzz==3.14.3")),
        Library(pypi=PythonPyPiLibrary(package="opencv-python-headless==4.8.1.78")),
        
        # Azure integration libraries
        Library(pypi=PythonPyPiLibrary(package="azure-storage-blob>=12.19.0")),
        Library(pypi=PythonPyPiLibrary(package="azure-identity>=1.15.0")),
        Library(pypi=PythonPyPiLibrary(package="azure-servicebus>=7.11.0")),
    ]


def get_target_schema(target: str) -> str:
    """Map DAB target to schema name."""
    target_mapping = {
        "prod-sp": "prod",
        "dev-sp": "dev",
    }
    return target_mapping.get(target, target)


def find_existing_cluster(client: WorkspaceClient, cluster_name: str) -> Optional[str]:
    """Find existing cluster by name and return cluster ID if found."""
    try:
        clusters = client.clusters.list()
        for cluster in clusters:
            if cluster.cluster_name == cluster_name:
                return cluster.cluster_id
    except Exception as e:
        print(f"    ✗ Failed to list clusters: {e}")
    return None


def update_existing_cluster(client: WorkspaceClient, cluster_id: str, cluster_name: str, config: Dict) -> bool:
    """Update an existing cluster with new configuration."""
    try:
        # Update custom tags with environment
        custom_tags = config["custom_tags"].copy()
        
        print(f"    Updating cluster configuration...")
        client.clusters.edit(
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            spark_version=config["spark_version"],
            node_type_id=config["node_type_id"],
            num_workers=config["num_workers"],
            data_security_mode=config["data_security_mode"],
            runtime_engine=config["runtime_engine"],
            autotermination_minutes=config["autotermination_minutes"],
            spark_conf=config["spark_conf"],
            spark_env_vars=config["spark_env_vars_template"],
            custom_tags=custom_tags,
        )
        print(f"    ✓ Updated cluster configuration")
        return True
    except Exception as e:
        print(f"    ✗ Failed to update cluster configuration: {e}")
        return False


def create_clusters(client: WorkspaceClient, target: str) -> Dict[str, str]:
    """Create interactive clusters with JSL configuration."""
    configs = load_cluster_configs()
    schema = get_target_schema(target)
    cluster_ids = {}
    
    print(f"Creating interactive clusters for target: {target}")
    
    for cluster_key, config in configs.items():
        cluster_name = config["cluster_name_template"]
        
        # Update custom tags with environment
        custom_tags = config["custom_tags"].copy()
        custom_tags["environment"] = schema
        
        print(f"  Processing cluster: {cluster_name}")
        
        # Check if cluster already exists
        existing_cluster_id = find_existing_cluster(client, cluster_name)
        
        if existing_cluster_id:
            print(f"    ✓ Found existing cluster with ID: {existing_cluster_id}")
            cluster_ids[cluster_key] = existing_cluster_id
            
            # Update existing cluster configuration
            if update_existing_cluster(client, existing_cluster_id, cluster_name, config):
                # Start cluster if it's not running, then wait for it to be running
                print(f"    Starting cluster if needed...")
                try:
                    cluster_info = client.clusters.get(existing_cluster_id)
                    if cluster_info.state and "TERMINATED" in str(cluster_info.state):
                        print(f"    Cluster is terminated, starting it...")
                        client.clusters.start(existing_cluster_id)
                    
                    print(f"    Waiting for cluster to be running...")
                    client.clusters.wait_get_cluster_running(existing_cluster_id)
                    
                    # Synchronize libraries (remove unwanted, install desired)
                    print(f"    Synchronizing JSL libraries...")
                    sync_libraries(client, existing_cluster_id)
                    
                except Exception as e:
                    print(f"    ⚠️ Library installation failed: {e}")
                
                # Always try to set cluster permissions, regardless of library status
                try:
                    print(f"    Setting cluster permissions...")
                    set_cluster_permissions(client, existing_cluster_id)
                except Exception as e:
                    print(f"    ⚠️ Permission setting failed: {e}")
            else:
                print(f"    ✗ Failed to update cluster configuration")
        else:
            print(f"    Creating new cluster...")
            try:
                # Create cluster with JSL secrets
                print(f"      ✓ Including JSL environment variables with secret references")
                    
                response = client.clusters.create(
                    cluster_name=cluster_name,
                    spark_version=config["spark_version"],
                    node_type_id=config["node_type_id"],
                    num_workers=config["num_workers"],
                    data_security_mode=config["data_security_mode"],
                    runtime_engine=config["runtime_engine"],
                    autotermination_minutes=config["autotermination_minutes"],
                    spark_conf=config["spark_conf"],
                    spark_env_vars=config["spark_env_vars_template"],
                    custom_tags=custom_tags,
                ).result()
                cluster_id = response.cluster_id
                cluster_ids[cluster_key] = cluster_id
                print(f"      ✓ Created cluster {cluster_name} with ID: {cluster_id}")
                
                # Install libraries after cluster creation and wait for it to be running
                print(f"      Waiting for cluster to be running...")
                client.clusters.wait_get_cluster_running(cluster_id)
                
                print(f"      Synchronizing JSL libraries on {cluster_name}...")
                sync_libraries(client, cluster_id)
                
                # Set cluster permissions
                print(f"      Setting cluster permissions...")
                set_cluster_permissions(client, cluster_id)
                
            except Exception as e:
                print(f"      ✗ Failed to create cluster {cluster_name}: {e}")
            
    return cluster_ids


def delete_clusters(client: WorkspaceClient, target: str) -> None:
    """Delete interactive clusters."""
    configs = load_cluster_configs()
    schema = get_target_schema(target)
    
    print(f"Deleting interactive clusters for target: {target}")
    
    # Find clusters by name pattern
    clusters = client.clusters.list()
    
    for cluster_key, config in configs.items():
        cluster_name = config["cluster_name_template"].format(schema=schema)
        
        # Find matching cluster
        matching_cluster = None
        for cluster in clusters:
            if cluster.cluster_name == cluster_name:
                matching_cluster = cluster
                break
                
        if matching_cluster:
            print(f"  Deleting cluster: {cluster_name} (ID: {matching_cluster.cluster_id})")
            try:
                client.clusters.permanent_delete(cluster_id=matching_cluster.cluster_id)
                print(f"    ✓ Deleted cluster {cluster_name}")
            except Exception as e:
                print(f"    ✗ Failed to delete cluster {cluster_name}: {e}")
        else:
            print(f"  Cluster not found: {cluster_name}")


def install_libraries(client: WorkspaceClient, cluster_id: str) -> None:
    """Install JSL libraries on a cluster."""
    libraries = get_jsl_libraries()
    
    try:
        client.libraries.install(cluster_id=cluster_id, libraries=libraries)
        print(f"    ✓ Library installation initiated for cluster {cluster_id}")
    except Exception as e:
        print(f"    ✗ Failed to install libraries on cluster {cluster_id}: {e}")


def sync_libraries(client: WorkspaceClient, cluster_id: str) -> None:
    """Synchronize cluster libraries - remove unwanted, install desired."""
    desired_libraries = get_jsl_libraries()
    
    try:
        # Get current library status
        current_status = client.libraries.cluster_status(cluster_id=cluster_id)
        
        # Build sets of desired library identifiers
        desired_jars = set()
        desired_whls = set() 
        desired_pypi = set()
        
        for lib in desired_libraries:
            if lib.jar:
                desired_jars.add(lib.jar)
            elif lib.whl:
                desired_whls.add(lib.whl)
            elif lib.pypi:
                desired_pypi.add(lib.pypi.package)
        
        # Find libraries to uninstall
        libraries_to_uninstall = []
        
        # current_status is a list of LibraryFullStatus objects directly
        for lib_status in current_status:
            lib = lib_status.library
            should_remove = False
            
            if lib.jar and lib.jar not in desired_jars:
                should_remove = True
                print(f"    Will remove JAR: {lib.jar}")
            elif lib.whl and lib.whl not in desired_whls:
                should_remove = True
                print(f"    Will remove WHL: {lib.whl}")
            elif lib.pypi and lib.pypi.package not in desired_pypi:
                should_remove = True
                print(f"    Will remove PyPI: {lib.pypi.package}")
                
            if should_remove:
                libraries_to_uninstall.append(lib)
        
        # Uninstall unwanted libraries
        if libraries_to_uninstall:
            print(f"    Uninstalling {len(libraries_to_uninstall)} unwanted libraries...")
            client.libraries.uninstall(cluster_id=cluster_id, libraries=libraries_to_uninstall)
        else:
            print(f"    No libraries to uninstall")
            
        # Install desired libraries (this will skip already installed ones)
        print(f"    Installing/updating desired libraries...")
        client.libraries.install(cluster_id=cluster_id, libraries=desired_libraries)
        
        print(f"    ✓ Library synchronization initiated for cluster {cluster_id}")
        
    except Exception as e:
        print(f"    ✗ Failed to synchronize libraries on cluster {cluster_id}: {e}")


def check_library_status(client: WorkspaceClient, cluster_id: str) -> None:
    """Check the status of library installations on a cluster."""
    try:
        status = client.libraries.cluster_status(cluster_id=cluster_id)
        print(f"  Library status for cluster {cluster_id}:")
        
        # status is a list of LibraryFullStatus objects directly
        for lib_status in status:
            library_info = ""
            if lib_status.library.jar:
                library_info = f"JAR: {lib_status.library.jar}"
            elif lib_status.library.whl:
                library_info = f"WHL: {lib_status.library.whl}"
            elif lib_status.library.pypi:
                library_info = f"PyPI: {lib_status.library.pypi}"
            
            print(f"    {library_info}: {lib_status.status}")
            
    except Exception as e:
        print(f"    ✗ Failed to get library status for cluster {cluster_id}: {e}")


def get_cluster_status(client: WorkspaceClient, target: str) -> None:
    """Get status of interactive clusters."""
    configs = load_cluster_configs()
    schema = get_target_schema(target)
    
    print(f"Interactive cluster status for target: {target}")
    
    # List all clusters
    clusters = client.clusters.list()
    
    for cluster_key, config in configs.items():
        cluster_name = config["cluster_name_template"].format(schema=schema)
        
        # Find matching cluster
        matching_cluster = None
        for cluster in clusters:
            if cluster.cluster_name == cluster_name:
                matching_cluster = cluster
                break
                
        if matching_cluster:
            print(f"  {cluster_name}:")
            print(f"    ID: {matching_cluster.cluster_id}")
            print(f"    State: {matching_cluster.state}")
            print(f"    Runtime: {matching_cluster.spark_version}")
            
            # Check library status if cluster is running
            if matching_cluster.state and "RUNNING" in str(matching_cluster.state):
                check_library_status(client, matching_cluster.cluster_id)
        else:
            print(f"  {cluster_name}: NOT FOUND")


def install_libraries_by_name(client: WorkspaceClient, cluster_name: str) -> None:
    """Install libraries on a cluster by name."""
    # Find cluster by name
    clusters = client.clusters.list()
    matching_cluster = None
    
    for cluster in clusters:
        if cluster.cluster_name == cluster_name:
            matching_cluster = cluster
            break
            
    if not matching_cluster:
        print(f"Cluster not found: {cluster_name}")
        return
        
    print(f"Installing JSL libraries on cluster: {cluster_name}")
    install_libraries(client, matching_cluster.cluster_id)


def main():
    parser = argparse.ArgumentParser(
        description="Manage HPS Clinical Notes interactive clusters with JSL libraries"
    )
    parser.add_argument(
        "command", 
        choices=["create", "delete", "status", "install-libraries"],
        help="Command to execute"
    )
    parser.add_argument(
        "--target", 
        default="prod-sp",
        help="DAB target (prod-sp, dev-sp)"
    )
    parser.add_argument(
        "--profile",
        help="Databricks CLI profile to use"
    )
    parser.add_argument(
        "--cluster-name",
        help="Cluster name for install-libraries command"
    )
    
    args = parser.parse_args()
    
    # Initialize Databricks client
    client_kwargs = {}
    if args.profile:
        client_kwargs["profile"] = args.profile
        
    try:
        client = WorkspaceClient(**client_kwargs)
    except Exception as e:
        print(f"Failed to initialize Databricks client: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == "create":
            cluster_ids = create_clusters(client, args.target)
            print(f"\nCluster creation completed. IDs: {cluster_ids}")
            
        elif args.command == "delete":
            delete_clusters(client, args.target)
            print("\nCluster deletion completed.")
            
        elif args.command == "status":
            get_cluster_status(client, args.target)
            
        elif args.command == "install-libraries":
            if not args.cluster_name:
                print("--cluster-name is required for install-libraries command")
                sys.exit(1)
            install_libraries_by_name(client, args.cluster_name)
            
    except Exception as e:
        print(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()