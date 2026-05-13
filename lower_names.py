import pandas

# Germany job assignments split
def split_germany_job_assignments(data, filename):
    germany_mask = data["business unit description"].str.strip().str.lower() == "joby germany gmbh"
    germany_data = data[germany_mask].copy()
    remaining_data = data[~germany_mask]
    if not germany_data.empty:
        germany_filename = filename.replace(".csv", "_JobyGermany.csv")
        germany_data["tenantmember"] = "jbg"
        germany_data.to_csv(germany_filename)
    return remaining_data

# Germany users split
def split_germany_users(data, filename):
    germany_mask = data["business unit description"].str.strip().str.lower() == "joby germany gmbh"
    germany_data = data[germany_mask].copy()
    remaining_data = data[~germany_mask]
    if not germany_data.empty:
        germany_filename = filename.replace(".csv", "_JobyGermany.csv")
        germany_data["tenantmember"] = "jbg"
        germany_data.to_csv(germany_filename)
    return remaining_data


def main():
    # Get filename through stdin
    filenname = input().strip('"').strip("'")

    while (filenname != 'q'):
        print("...working...")
        data = pandas.read_csv(filenname)
        # Job Assignments file
        if "job assignments" in filenname.lower():
            data = data[~(data["useridnumber"].isna() | (data["useridnumber"] == ""))]
            data = split_germany_job_assignments(data, filenname)
            data["Manager email"] = data["Manager email"].fillna("#N/A")
            for name_index in data.index:
                data.loc[name_index, "Manager email"] = data["Manager email"][name_index].lower()
            for name_index in data.index:
                data.loc[name_index, "useridnumber"] = data["useridnumber"][name_index].lower()
        # Users file
        else:
            data = data[~(data["idnumber"].isna() | (data["idnumber"] == ""))]
            data = split_germany_users(data, filenname)
            for name_index in data.index:
                data.loc[name_index, "idnumber"] = data["idnumber"][name_index].lower()
            for name_index in data.index:
                data.loc[name_index, "email"] = data["email"][name_index].lower()

        data.to_csv(filenname)

        print("Success!") # Can take a while to perform above tasks, so input is ready after this message is displayed

        filenname = input().strip('"')

if __name__ == "__main__":
    main()