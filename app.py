import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
import io
from copy import deepcopy
import platform

st.set_page_config(page_title="SRE Team Shift Roster", layout="wide")

# Application title and description
st.title("SRE Team Shift Roster Generator")
st.markdown("😶‍🌫️")

# Initialize session state
if 'team_members' not in st.session_state:
    st.session_state.team_members = []
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None
if 'month_year' not in st.session_state:
    st.session_state.month_year = datetime.now()

# Sidebar for controls
with st.sidebar:
    st.header("Roster Settings")
    
    # Month and Year selection
    month_year = st.date_input(
        "Select Month and Year",
        st.session_state.month_year
    )
    # Only keep month and year info
    month_year = datetime(month_year.year, month_year.month, 1)
    st.session_state.month_year = month_year
    
    # Shift types
    st.subheader("Available Shift Types")
    shift_types = ['SA', 'SB', 'SC', 'WFH', 'Leave', 'WO', '-']
    st.write(", ".join(shift_types))
    
    # Team member management
    st.subheader("Team Members")
    new_member = st.text_input("Add team member")
    
    if st.button("Add Member"):
        if new_member and new_member not in st.session_state.team_members:
            st.session_state.team_members.append(new_member)
    
    # Display and manage team members
    for i, member in enumerate(st.session_state.team_members):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"{i+1}. {member}")
        with col2:
            if st.button("Remove", key=f"remove_{i}"):
                st.session_state.team_members.remove(member)
                st.rerun()

# Function to create a calendar dataframe
def create_calendar_df(month_year, team_members):
    # Get the number of days in the month
    _, days_in_month = calendar.monthrange(month_year.year, month_year.month)
    
    # Create date range for the month
    date_range = [month_year + timedelta(days=i) for i in range(days_in_month)]
    
    # Create date columns - with platform-compatible formatting
    # Windows doesn't support the "-" flag in strftime
    date_cols = []
    day_cols = []
    
    for d in date_range:
        # For day of month without leading zeros
        if platform.system() == 'Windows':
            day = str(d.day)  # No leading zeros
        else:
            day = d.strftime("%-d")
            
        month_abbr = d.strftime("%b")
        date_cols.append(f"{day}-{month_abbr}")
        day_cols.append(d.strftime("%a"))
    
    # Create the DataFrame structure
    df = pd.DataFrame(index=team_members)
    
    # Add date and day name as multi-index columns
    for i, (date, day) in enumerate(zip(date_cols, day_cols)):
        df[date] = 'SA'  # Default value
    
    return df, date_cols, day_cols

# Function to apply default shifts based on pattern selection
def apply_default_shifts(df, team_member, default_shift, weekend_pattern, date_cols, day_cols):
    weekday_mapping = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    
    # Map weekend pattern to days that should have WO (Week Off)
    weekend_days = []
    if weekend_pattern == 'Sat-Sun':
        weekend_days = ['Sat', 'Sun']
    elif weekend_pattern == 'Sun-Mon':
        weekend_days = ['Sun', 'Mon']
    elif weekend_pattern == 'Fri-Sat':
        weekend_days = ['Fri', 'Sat']
    
    # Apply the default shifts
    for i, (date, day) in enumerate(zip(date_cols, day_cols)):
        day_abbr = day[:3]  # Get first 3 chars (Mon, Tue, etc.)
        if day_abbr in weekend_days:
            df.loc[team_member, date] = 'WO'
        else:
            df.loc[team_member, date] = default_shift
    
    return df

# Main area for roster creation and display
if st.session_state.team_members:
    # Initialize or update the roster dataframe
    roster_df, date_cols, day_cols = create_calendar_df(st.session_state.month_year, st.session_state.team_members)
    
    if st.session_state.roster_df is None or st.session_state.roster_df.index.tolist() != st.session_state.team_members:
        st.session_state.roster_df = roster_df
    else:
        # Update with any new columns but keep existing values
        existing_df = st.session_state.roster_df
        updated_df, _, _ = create_calendar_df(st.session_state.month_year, st.session_state.team_members)
        
        # Keep existing values for columns that already exist
        for col in updated_df.columns:
            if col in existing_df.columns:
                updated_df[col] = existing_df[col]
        
        st.session_state.roster_df = updated_df
    
    # Display the header row with days of the week
    st.markdown("## Shift Roster")
    
    # Create a template to show day names
    template_df = pd.DataFrame([day_cols], columns=date_cols, index=["Day"])
    st.dataframe(template_df, use_container_width=True)
    
    # Default shift pattern section (New feature)
    st.markdown("## Quick Shift Assignment")
    st.markdown("Set default shifts for team members based on patterns")
    
    with st.form("default_shifts_form"):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            selected_member = st.selectbox(
                "Select Team Member",
                options=st.session_state.team_members
            )
        
        with col2:
            default_shift = st.selectbox(
                "Default Shift",
                options=['SA', 'SB', 'SC', 'WFH']
            )
        
        with col3:
            weekend_pattern = st.selectbox(
                "Weekend Pattern",
                options=['Sat-Sun', 'Sun-Mon', 'Fri-Sat']
            )
        
        apply_defaults = st.form_submit_button("Apply Default Shifts")
        
        if apply_defaults:
            # Apply the default shifts
            temp_df = deepcopy(st.session_state.roster_df)
            updated_df = apply_default_shifts(temp_df, selected_member, default_shift, weekend_pattern, date_cols, day_cols)
            st.session_state.roster_df = updated_df
            st.success(f"Applied {default_shift} with {weekend_pattern} off for {selected_member}")
    
    # Create form for manual editing with dropdowns
    with st.form("roster_form"):
        st.markdown("## Manual Shift Assignment")
        edited_df = deepcopy(st.session_state.roster_df)
        
        for member in st.session_state.team_members:
            st.markdown(f"### {member}")
            cols = st.columns(len(date_cols))
            
            for i, date in enumerate(date_cols):
                with cols[i]:
                    current_value = edited_df.loc[member, date] if date in edited_df.columns else 'SA'
                    new_value = st.selectbox(
                        f"{date}",
                        options=shift_types,
                        index=shift_types.index(current_value) if current_value in shift_types else 0,
                        key=f"{member}_{date}"
                    )
                    edited_df.loc[member, date] = new_value
        
        submit = st.form_submit_button("Update Roster")
        if submit:
            st.session_state.roster_df = edited_df
            st.success("Roster updated successfully!")
    
    # Display the current roster
    st.markdown("## Current Roster")
    st.dataframe(st.session_state.roster_df, use_container_width=True)
    
    # Add download button for Excel export
    if st.session_state.roster_df is not None:
        # Prepare Excel file
        output = io.BytesIO()
        
        # Create a writer with xlsxwriter engine
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Convert DataFrame to Excel
            export_df = st.session_state.roster_df.copy()
            
            # Add a header row for day names
            days_df = pd.DataFrame([day_cols], columns=date_cols, index=["Day"])
            final_df = pd.concat([days_df, export_df])
            
            final_df.to_excel(writer, sheet_name='Roster')
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Roster']
            
            # Define formats with updated colors as requested
            header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'border': 1})
            day_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'border': 1})
            
            # Define formats for each shift type
            sa_format = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1})  # Light green
            sb_format = workbook.add_format({'bg_color': '#FFEB9C', 'border': 1})  # Light orange
            sc_format = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})  # White
            wo_format = workbook.add_format({'bg_color': '#FFFF99', 'border': 1})  # Light yellow
            leave_format = workbook.add_format({'bg_color': '#FFC7CE', 'border': 1})  # Light red
            wfh_format = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1})  # Light blue
            blank_format = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})  # White for "-"
            
            # Apply formats to header and row names
            for col_num, value in enumerate(final_df.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
                # Add the day (Mon, Tue, etc.) in the cell below the date
                worksheet.write(1, col_num + 1, day_cols[col_num], day_format)
            
            # Apply conditional formatting based on values - start from row 2 (after the day header)
            for row_num in range(2, len(final_df) + 1):
                worksheet.write(row_num, 0, final_df.index[row_num - 1], header_format)
                
                for col_num, value in enumerate(final_df.iloc[row_num - 1]):
                    if value == 'SA':
                        worksheet.write(row_num, col_num + 1, value, sa_format)
                    elif value == 'SB':
                        worksheet.write(row_num, col_num + 1, value, sb_format)
                    elif value == 'SC':
                        worksheet.write(row_num, col_num + 1, value, sc_format)
                    elif value == 'WO':
                        worksheet.write(row_num, col_num + 1, value, wo_format)
                    elif value == 'Leave':
                        worksheet.write(row_num, col_num + 1, value, leave_format)
                    elif value == 'WFH':
                        worksheet.write(row_num, col_num + 1, value, wfh_format)
                    elif value == '-':
                        worksheet.write(row_num, col_num + 1, value, blank_format)
                    else:
                        worksheet.write(row_num, col_num + 1, value, blank_format)
                        
            # Auto-adjust column widths
            for i, col in enumerate(final_df.columns):
                column_width = max(len(col) + 2, 10)
                worksheet.set_column(i + 1, i + 1, column_width)
            
            # Set wider first column for names
            worksheet.set_column(0, 0, 15)
        
        # Provide download button
        output.seek(0)
        month_name = st.session_state.month_year.strftime("%B_%Y")
        st.download_button(
            label="Download Roster as Excel",
            data=output,
            file_name=f"SRE_Shift_Roster_{month_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Please add team members using the sidebar to create a roster.")

# Quick start guide
with st.expander("How to Use This Tool"):
    st.markdown("""
    1. **Add Team Members**: Use the sidebar to add all SRE team members
    2. **Select Month and Year**: Choose the month for which you want to create the roster
    3. **Apply Default Shifts**: 
       - Select a team member
       - Choose their default shift type (SA, SB, SC, etc.)
       - Select weekend pattern (Sat-Sun, Sun-Mon, Fri-Sat)
       - Click "Apply Default Shifts" to automatically apply the pattern
    4. **Fine-tune Shifts**: Use the manual assignment section to adjust individual days as needed
    5. **Update Roster**: Click the "Update Roster" button to save your changes
    6. **Download**: Download the completed roster as an Excel file
    
    **Shift Type Abbreviations**:
    - SA: Shift A (Light Green)
    - SB: Shift B (Light Orange)
    - SC: Shift C (White)
    - WFH: Work From Home (Light Blue)
    - Leave: On leave (Light Red)
    - WO: Week Off (Light Yellow)
    - -: Not scheduled (White)
    """)
