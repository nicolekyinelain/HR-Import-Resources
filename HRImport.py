"""
HR Import module for processing and transforming HR data files.

Converts names to lowercase and separates Joby Germany users into tenant-specific files.
Routes file processing based on filename keywords ("Job Assignments" vs "Users").
"""
import pandas


class HRImport:
    """
    Process HR CSV files with tenant splitting and data normalization.
    
    Performs file-type specific transformations:
    - Job Assignments: validates useridnumber, filters test accounts, lowercases fields
    - Users: splits tenant-specific records, validates idnumber, lowercases fields
    
    Attributes:
        filename (str): Path to the CSV file being processed
        data (pandas.DataFrame): CSV data loaded into memory
    """

    def __init__(self, filename: str) -> None:
        """
        Initialize HRImport with a CSV file.

        Args:
            filename: Path to the CSV file to process
        """
        self.filename: str = filename
        try:
            self.data: pandas.DataFrame = pandas.read_csv(filename)
        except Exception as e:
            raise RuntimeError(f"Failed to load data from {filename}") from e



    def _split_tenant(self, business_unit_description: str, tenant_id: str) -> pandas.DataFrame:
        """
        Separate tenant-specific records into standalone CSV files.
        
        For each tenant, filters records matching the business_unit_description (case-insensitive),
        writes them to a new CSV with tenant suffix and adds 'tenantmember' column for auto-enrollment.
        Returns the main dataframe with tenant records removed.
        
        Args:
            business_unit_description: Business unit identifier to filter on (e.g., "joby germany gmbh")
            tenant_id: Tenant code to add in output file naming and tenantmember column (e.g., "jbg")
            
        Returns:
            DataFrame with tenant-specific records removed (ready for next tenant split or final output)
        """
        # Create boolean mask: True where business unit matches (case-insensitive), False elsewhere
        # Uses str accessor for vectorized string operations on entire column
        tenant_mask = self.data["business unit description"].str.strip().str.lower() == business_unit_description.lower()
        
        # Extract matching records into separate dataframe for tenant-specific output file
        tenant_data = self.data.loc[tenant_mask, :].copy()
        
        # Retain non-matching records as the new main dataset for subsequent processing
        remaining_data = self.data.loc[~tenant_mask, :]
        
        # Write tenant records to new CSV with tenant identifier in filename if records found
        if not tenant_data.empty:
            tenant_filename = self.filename.replace(".csv", f" {tenant_id}.csv")
            tenant_data["tenantmember"] = tenant_id  # Add column for auto-enrollment in downstream systems
            tenant_data.to_csv(tenant_filename, index=False)

            tentant_import = HRImport(tenant_filename)
            tentant_import.run([]) # Process tenant-specific file without further tenant splitting
            
        return remaining_data



    def _job_assignments(self) -> None:
        """
        Transform Job Assignments file: validate required fields, standardize casing, filter test accounts.
        
        Removes rows with missing useridnumber, fills NaN manager emails with "#N/A" placeholder,
        converts manager email and useridnumber to lowercase, and filters out known test accounts.
        """
        # Remove rows where useridnumber is missing, empty, or NaN - this field is required downstream
        self.data = self.data.loc[
            ~(self.data["useridnumber"].isna() | (self.data["useridnumber"] == "")),
            :
        ].copy()
        
        # Replace NaN values in Manager email with placeholder for downstream processing
        # Systems may expect a specific indicator rather than null to distinguish missing from invalid
        self.data["Manager email"] = self.data["Manager email"].fillna("#N/A")
        
        # Drop suspended users
        self.data = self.data.loc[self.data["suspended"] != 1, :].copy()

        # Normalize email addresses and IDs to lowercase for consistent matching/comparison
        self.data["Manager email"] = self.data["Manager email"].str.lower()
        self.data["useridnumber"] = self.data["useridnumber"].str.lower()

        # Filter out known problematic accounts
        dont_suspend = pandas.read_csv("dont_suspend.csv")["email"].tolist()
        self.data = self.data.loc[~self.data["useridnumber"].isin(dont_suspend), :].copy()

        return

    def _users(self, tenants: list[dict[str, str]]) -> None:
        """
        Transform Users file: validate required fields, split by tenant, standardize casing, filter test accounts.
        
        Removes rows with missing idnumber, iterates through configured tenants to split records
        into tenant-specific files, then converts idnumber and email to lowercase and filters test accounts.
        
        Args:
            tenants: List of tenant configuration dicts with keys:
                     - tenant_id: tenant code identifier
                     - business_unit_description: business unit to match for splitting
                     - tenant_name: human-readable tenant name
        """
        # Determine whther or not the file being processed is a terminated employee file based on filename keyword - this is used for removing the 'deleted' column and renaming the 'suspended' column
        terminated = "terminated" in self.filename.lower()

        # Remove rows where idnumber is missing or empty - this field is required for user identification
        self.data = self.data.loc[
            ~(self.data["idnumber"].isna() | (self.data["idnumber"] == "")),
            :
        ].copy()
        
        # Split data for each configured tenant into separate CSV files with tenantmember assignment
        # Iteratively removes matching records from self.data in each iteration
        for tenant in tenants:
            self.data = self._split_tenant(tenant["business_unit_description"], tenant["tenant_id"])
        
        if terminated: # If processing a terminated employee file, filter to suspended users and rename columns accordingly
            self.data = self.data.loc[self.data["suspended"] == 1, :].copy()
            self.data = self.data.drop(columns=["deleted"])
            self.data = self.data.rename(columns={"suspended": "deleted"})
        else: # For active employee files, filter out suspended users
            self.data = self.data.loc[self.data["suspended"] == 0, :].copy()

        # Normalize email addresses and IDs to lowercase for consistent matching/comparison
        self.data["idnumber"] = self.data["idnumber"].str.lower()
        self.data["email"] = self.data["email"].str.lower()
        self.data["tenantmember"] = None  # Clear tenantmember for non-tenant-specific records to prevent accidental enrollment

        # Filter out known problematic accounts
        dont_suspend = pandas.read_csv("dont_suspend.csv")["email"].tolist()
        self.data = self.data.loc[~self.data["idnumber"].isin(dont_suspend), :].copy()

        return
    

    def run(self, tenants: list[dict[str, str]]) -> None:
        """
        Execute appropriate file transformation and save results.
        
        Routes to file-type-specific processing based on filename keywords, then persists
        transformed dataframe back to the original CSV file.
        
        Args:
            tenants: List of tenant configurations passed to file-type-specific processors

        Raises:
            ValueError: If filename contains neither 'Job Assignments' nor 'Users' keyword
        """
        print(f"Working {self.filename}...")

        # Route to appropriate processing based on filename keyword to determine file type
        # Case-insensitive matching allows for variations in naming conventions
        if "job assignments" in self.filename.lower():
            self._job_assignments()
        elif "users" in self.filename.lower():
            self._users(tenants)
        else:
            raise ValueError("Filename must contain either 'Job Assignments' or 'Users' to determine the type of file being processed.")

        # Persist transformed data back to original file location
        self.data.to_csv(self.filename, index=False)

        # Print success message after potentially long-running operations complete
        print(f"Successfully processed file {self.filename}.")

        return