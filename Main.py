"""
HR data file import CLI.

Entry point for interactive file processing with tenant selection via command-line arguments.
Processes multiple CSV files sequentially with tenant-specific splitting and normalization.
"""
import os
import sys
import shutil
import Tenants
import HRImport

QUIT_CRITERIA = {"q", "quit", "exit"}

def usage() -> None:
    """
    Print usage instructions for the CLI.
    
    Provides guidance on how to run the script with optional tenant filtering and how to input filenames.
    """
    print("Usage: python Main.py [tenant_id ...]")
    print("Example: python Main.py jbg")
    print("Then enter CSV filenames to process (enter 'q' to quit)")


def main() -> None:
    """
    Interactive CLI for HR file processing with tenant filtering.
    
    CLI Usage:
        python Main.py [tenant_id ...]  (optional tenant IDs to filter)
        Then enter CSV filenames to process (enter 'q' to quit)
        
    Workflow:
        1. Load all available tenants from tenants.json
        2. Parse optional CLI arguments to filter to specific tenant(s)
        3. Loop: prompt for filename, validate with selected tenants, process file, repeat until 'q'
    
    Examples:
        python Main.py                    # Process files with no tenant splitting
        python Main.py jbg               # Process files only splitting for 'jbg' tenant
        python Main.py jbg embraer       # Process files splitting for both tenants
    
    Raises:
        ValueError: If tenant_id provided via CLI is not found in tenants.json
    """
    # Load all available tenants from configuration file
    tenants: list[dict[str, str]] = Tenants.load_tenants()
    use_tenants: list[dict[str, str]] = []
    
    # Parse optional CLI arguments to select specific tenants for processing
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            # Normalize argument to lowercase for case-insensitive matching against tenant_id
            normalized_arg: str = arg.lower()
            
            # Search for tenant(s) matching the provided ID (supports filtering/validation by tenant_id)
            # List comprehension filters tenants where tenant_id exactly matches normalized argument
            matches: list[dict[str, str]] = [tenant for tenant in tenants if tenant["tenant_id"] == normalized_arg]
            
            # Handle special help cases without processing any tenant filtering or file input
            if arg == "-h" or arg == "--help":
                usage()
                return
            
            # The elephant
            if arg == "-elephant":
                print("Address me...")
                return
            
            # If tenant ID found, append matching configurations; otherwise raise error for invalid input
            if matches:
                for tenant in matches:
                    use_tenants.append(tenant)
                    print(f"Selected tenant for processing: {tenant['tenant_name']} (ID: {tenant['tenant_id']})")
            else:
                raise ValueError(f"Tenant ID '{arg}' not found")

    # Loop until user enters 'q' to quit, processing each CSV file with the selected tenants
    # Input stripping removes surrounding quotes that file explorers often add when copying paths
    filename: str = input().strip('"').strip("'")
    
    while filename.lower() not in QUIT_CRITERIA:
        # Backup original files to a separate directory to preserve unmodified data for auditing or reprocessing if needed
        try:
            oringial_files_dir = os.path.dirname(filename) + "/original_files"
            os.makedirs(oringial_files_dir, exist_ok=True)
            shutil.copy(filename, oringial_files_dir + "/" + "Original " + os.path.basename(filename))
        except FileNotFoundError as e:
            print(f"Warning: Failed to backup original file '{filename}' - {e}")

        # Instantiate HR import handler for this file and execute transformations with selected tenants
        hr_import: HRImport.HRImport = HRImport.HRImport(filename)
        hr_import.run(use_tenants)
        
        # Prompt for next filename (or 'q' to exit)
        filename = input().strip('"').strip("'")


if __name__ == "__main__":
    main()