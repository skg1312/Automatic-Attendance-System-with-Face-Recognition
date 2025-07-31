import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database.db_manager import DatabaseManager
import plotly.express as px
import plotly.graph_objects as go

class ReportsPage:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def render(self):
        st.title("📊 Attendance Reports & Analytics")
        st.markdown("Comprehensive attendance tracking and analytics dashboard")
        
        # Date range selector
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("End Date", value=date.today())
        
        with col3:
            if st.button("🔄 Refresh Data"):
                st.rerun()
        
        # Validate date range
        if start_date > end_date:
            st.error("Start date must be before end date")
            return
        
        # Get attendance data
        attendance_records = self.db_manager.get_attendance_records()
        
        # Filter records by date range with proper date handling
        filtered_records = []
        for record in attendance_records:
            try:
                record_date = record[6]  # Date field
                
                # Handle both string and date object types
                if isinstance(record_date, str):
                    # Parse string date
                    record_date_obj = datetime.strptime(record_date, '%Y-%m-%d').date()
                elif hasattr(record_date, 'date'):
                    # datetime object - extract date part
                    record_date_obj = record_date.date()
                else:
                    # Already a date object
                    record_date_obj = record_date
                
                # Check if date is in range
                if start_date <= record_date_obj <= end_date:
                    filtered_records.append(record)
                    
            except (ValueError, AttributeError, TypeError) as e:
                # Skip records with invalid dates
                st.warning(f"Skipping record with invalid date: {record_date}")
                continue
        
        # Display different report sections
        self._show_summary_stats(filtered_records, start_date, end_date)
        self._show_attendance_charts(filtered_records)
        self._show_detailed_reports(filtered_records)
        self._show_user_analytics(filtered_records)
    
    def _show_summary_stats(self, records, start_date, end_date):
        """Display summary statistics"""
        st.subheader("📈 Summary Statistics")
        
        # Calculate metrics
        total_users = len(self.db_manager.get_all_users())
        total_records = len(records)
        unique_attendees = len(set(record[2] for record in records))  # employee_id
        
        # Check-in/check-out counts
        check_ins = sum(1 for record in records if record[4])  # check_in_time
        check_outs = sum(1 for record in records if record[5])  # check_out_time
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("👥 Total Users", total_users)
        
        with col2:
            st.metric("📋 Total Records", total_records)
        
        with col3:
            st.metric("🎯 Unique Attendees", unique_attendees)
        
        with col4:
            st.metric("✅ Check-ins", check_ins)
        
        with col5:
            st.metric("🚪 Check-outs", check_outs)
        
        # Attendance rate
        if total_users > 0:
            attendance_rate = (unique_attendees / total_users) * 100
            st.metric("📊 Attendance Rate", f"{attendance_rate:.1f}%")
    
    def _show_attendance_charts(self, records):
        """Display attendance charts and visualizations"""
        st.subheader("📊 Attendance Visualizations")
        
        if not records:
            st.info("No attendance data available for the selected date range.")
            return
        
        # Prepare data for charts
        df_records = pd.DataFrame(records, columns=[
            'id', 'name', 'employee_id', 'department', 'check_in_time', 
            'check_out_time', 'date', 'confidence'
        ])
        
        # Convert date column
        df_records['date'] = pd.to_datetime(df_records['date'])
        
        # Daily attendance chart
        daily_attendance = df_records.groupby('date').size().reset_index(name='count')
        
        fig_daily = px.line(
            daily_attendance, 
            x='date', 
            y='count',
            title='Daily Attendance Trend',
            labels={'count': 'Number of Attendees', 'date': 'Date'}
        )
        fig_daily.update_traces(mode='markers+lines')
        st.plotly_chart(fig_daily, use_container_width=True)
        
        # Department-wise attendance
        if df_records['department'].notna().any():
            dept_attendance = df_records.groupby('department').size().reset_index(name='count')
            
            fig_dept = px.pie(
                dept_attendance,
                values='count',
                names='department',
                title='Department-wise Attendance Distribution'
            )
            st.plotly_chart(fig_dept, use_container_width=True)
        
        # Weekly attendance pattern
        df_records['day_of_week'] = df_records['date'].dt.day_name()
        weekly_attendance = df_records.groupby('day_of_week').size().reset_index(name='count')
        
        # Reorder days
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_attendance['day_of_week'] = pd.Categorical(weekly_attendance['day_of_week'], categories=day_order, ordered=True)
        weekly_attendance = weekly_attendance.sort_values('day_of_week')
        
        fig_weekly = px.bar(
            weekly_attendance,
            x='day_of_week',
            y='count',
            title='Weekly Attendance Pattern',
            labels={'count': 'Number of Attendees', 'day_of_week': 'Day of Week'}
        )
        st.plotly_chart(fig_weekly, use_container_width=True)
        
        # Hourly attendance pattern
        df_records['check_in_hour'] = pd.to_datetime(df_records['check_in_time']).dt.hour
        hourly_attendance = df_records.dropna(subset=['check_in_hour']).groupby('check_in_hour').size().reset_index(name='count')
        
        if not hourly_attendance.empty:
            fig_hourly = px.bar(
                hourly_attendance,
                x='check_in_hour',
                y='count',
                title='Check-in Time Distribution',
                labels={'count': 'Number of Check-ins', 'check_in_hour': 'Hour of Day'}
            )
            st.plotly_chart(fig_hourly, use_container_width=True)
    
    def _show_detailed_reports(self, records):
        """Show detailed attendance reports"""
        st.subheader("📋 Detailed Attendance Records")
        
        if not records:
            st.info("No records found for the selected date range.")
            return
        
        # Convert to DataFrame for better display
        df_records = pd.DataFrame(records, columns=[
            'ID', 'Name', 'Employee ID', 'Department', 'Check In', 
            'Check Out', 'Date', 'Confidence'
        ])
        
        # Format datetime columns
        df_records['Check In'] = pd.to_datetime(df_records['Check In']).dt.strftime('%H:%M:%S')
        df_records['Check Out'] = pd.to_datetime(df_records['Check Out']).dt.strftime('%H:%M:%S')
        df_records['Date'] = pd.to_datetime(df_records['Date']).dt.strftime('%Y-%m-%d')
        
        # Replace NaT with readable text
        df_records['Check In'] = df_records['Check In'].replace('NaT', 'Not checked in')
        df_records['Check Out'] = df_records['Check Out'].replace('NaT', 'Not checked out')
        
        # Format confidence
        df_records['Confidence'] = df_records['Confidence'].round(2)
        
        # Filters
        with st.expander("🔍 Filters"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name_filter = st.multiselect(
                    "Filter by Name",
                    options=sorted(df_records['Name'].unique())
                )
            
            with col2:
                dept_filter = st.multiselect(
                    "Filter by Department",
                    options=sorted(df_records['Department'].dropna().unique())
                )
            
            with col3:
                confidence_min = st.slider("Minimum Confidence", 0.0, 1.0, 0.0, 0.1)
        
        # Apply filters
        filtered_df = df_records.copy()
        
        if name_filter:
            filtered_df = filtered_df[filtered_df['Name'].isin(name_filter)]
        
        if dept_filter:
            filtered_df = filtered_df[filtered_df['Department'].isin(dept_filter)]
        
        filtered_df = filtered_df[filtered_df['Confidence'] >= confidence_min]
        
        # Display filtered data
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"attendance_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.write(f"**Total Records:** {len(filtered_df)}")
    
    def _show_user_analytics(self, records):
        """Show individual user analytics"""
        st.subheader("👤 Individual User Analytics")
        
        if not records:
            st.info("No data available for user analytics.")
            return
        
        # Get all users for selection
        users = self.db_manager.get_all_users()
        
        if not users:
            st.info("No users registered.")
            return
        
        # User selection
        selected_user = st.selectbox(
            "Select User for Detailed Analysis:",
            options=users,
            format_func=lambda x: f"{x[1]} ({x[2]})"  # name (employee_id)
        )
        
        if not selected_user:
            return
        
        user_id, user_name, employee_id, email, department, image_path, created_at = selected_user
        
        # Filter records for selected user
        user_records = [record for record in records if record[2] == employee_id]
        
        if not user_records:
            st.info(f"No attendance records found for {user_name}.")
            return
        
        # User information
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Name:** {user_name}")
            st.write(f"**Employee ID:** {employee_id}")
            st.write(f"**Department:** {department or 'N/A'}")
            st.write(f"**Email:** {email or 'N/A'}")
        
        with col2:
            st.write(f"**Total Attendance Days:** {len(user_records)}")
            avg_confidence = sum(record[7] for record in user_records if record[7]) / len(user_records)
            st.write(f"**Average Confidence:** {avg_confidence:.2f}")
            
            # Check-in/out stats
            check_ins = sum(1 for record in user_records if record[4])
            check_outs = sum(1 for record in user_records if record[5])
            st.write(f"**Check-ins:** {check_ins}")
            st.write(f"**Check-outs:** {check_outs}")
        
        # User attendance timeline
        user_df = pd.DataFrame(user_records, columns=[
            'id', 'name', 'employee_id', 'department', 'check_in_time', 
            'check_out_time', 'date', 'confidence'
        ])
        
        user_df['date'] = pd.to_datetime(user_df['date'])
        user_attendance = user_df.groupby('date').size().reset_index(name='count')
        
        fig_user = px.scatter(
            user_attendance,
            x='date',
            y='count',
            title=f'Attendance Timeline - {user_name}',
            labels={'count': 'Attendance Count', 'date': 'Date'}
        )
        fig_user.add_trace(
            go.Scatter(
                x=user_attendance['date'],
                y=user_attendance['count'],
                mode='lines',
                name='Trend',
                line=dict(color='red', width=2)
            )
        )
        st.plotly_chart(fig_user, use_container_width=True)
        
        # Recent attendance records
        st.write("**Recent Attendance Records:**")
        recent_records = user_df.tail(10).copy()
        recent_records['Check In'] = pd.to_datetime(recent_records['check_in_time']).dt.strftime('%H:%M:%S')
        recent_records['Check Out'] = pd.to_datetime(recent_records['check_out_time']).dt.strftime('%H:%M:%S')
        recent_records['Date'] = recent_records['date'].dt.strftime('%Y-%m-%d')
        
        display_cols = ['Date', 'Check In', 'Check Out', 'confidence']
        recent_records['Check In'] = recent_records['Check In'].replace('NaT', 'Not checked in')
        recent_records['Check Out'] = recent_records['Check Out'].replace('NaT', 'Not checked out')
        
        st.dataframe(
            recent_records[['Date', 'Check In', 'Check Out', 'confidence']].rename(columns={'confidence': 'Confidence'}),
            use_container_width=True
        )
