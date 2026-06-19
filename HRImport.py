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
        germany_mask = self.data["business unit description"].str.strip().str.lower() == business_unit_description.lower()
        
        # Extract matching records into separate dataframe for tenant-specific output file
        germany_data = self.data.loc[germany_mask, :].copy()
        
        # Retain non-matching records as the new main dataset for subsequent processing
        remaining_data = self.data.loc[~germany_mask, :]
        
        # Write tenant records to new CSV with tenant identifier in filename if records found
        if not germany_data.empty:
            germany_filename = self.filename.replace(".csv", f"_{tenant_id}.csv")
            germany_data["tenantmember"] = tenant_id  # Add column for auto-enrollment in downstream systems
            germany_data.to_csv(germany_filename)
            
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
        
        # Normalize email addresses and IDs to lowercase for consistent matching/comparison
        for name_index in self.data.index:
            # Remove suspended users from the file
            if self.data.loc[name_index, "suspended"] == 1:
                self.data = self.data.drop(name_index)
                continue

            self.data.loc[name_index, "Manager email"] = self.data["Manager email"][name_index].lower()
            self.data.loc[name_index, "useridnumber"] = self.data["useridnumber"][name_index].lower()
            
            # Filter out known test/admin accounts by idnumber to prevent test data in production
            if self.data.loc[name_index, "idnumber"] == "joeben@joby.aero" or self.data.loc[name_index, "idnumber"] == "patryck.chipman@joby.aero":
                self.data = self.data.drop(name_index)

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
        
        # Normalize email addresses and IDs to lowercase for consistent matching/comparison
        dont_suspend = pandas.read_csv("dont_suspend.csv")["email"].tolist()
        for name_index in self.data.index:
            # Remove active users from the file if the file is a terminated users file
            if self.data.loc[name_index, "deleted"] == 0 and terminated:
                self.data = self.data.drop(name_index)
                continue

            # Remove suspended users from the file if the file is not a terminated users file
            if self.data.loc[name_index, "suspended"] == 1 and not terminated:
                self.data = self.data.drop(name_index)
                continue

            self.data.loc[name_index, "idnumber"] = self.data["idnumber"][name_index].lower()
            self.data.loc[name_index, "email"] = self.data["email"][name_index].lower()
            self.data.loc[name_index, "tenantmember"] = None  # Clear tenantmember for non-tenant-specific records to prevent accidental enrollment
            
            # Filter out known test/admin accounts to prevent test data in production systems
            if self.data.loc[name_index, "idnumber"] in dont_suspend:
                self.data = self.data.drop(name_index)

        # Remove the 'deleted' column and rename 'suspended' column to 'deleted'
        if terminated:
            self.data = self.data.drop(columns=["deleted"])
            self.data = self.data.rename(columns={"suspended": "deleted"})

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
        print("...working...")

        # Route to appropriate processing based on filename keyword to determine file type
        # Case-insensitive matching allows for variations in naming conventions
        if "job assignments" in self.filename.lower():
            self._job_assignments()
        elif "users" in self.filename.lower():
            self._users(tenants)
        else:
            raise ValueError("Filename must contain either 'Job Assignments' or 'Users' to determine the type of file being processed.")

        # Persist transformed data back to original file location
        self.data.to_csv(self.filename)

        # Print success message after potentially long-running operations complete
        print("Success!")

        return