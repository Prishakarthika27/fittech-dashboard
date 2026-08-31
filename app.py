"""
FitTech: Fitness App Usage & Calorie Burn Patterns Dashboard
--------------------------------------------------------------
Run in Google Colab:
    !pip install streamlit plotly -q
    %%writefile app.py   <-- (paste this whole file)
    !streamlit run app.py & npx localtunnel --port 8501

Or run locally:
    pip install streamlit plotly openpyxl
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="FitTech Dashboard", layout="wide", page_icon="🏋️")

DATA_PATH = "Combined Dataset For Project only.xlsx"  # change if your filename differs

# ----------------------------------------------------------------------------
# 1. LOAD DATA
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(file):
    activity = pd.read_excel(file, sheet_name="Activity")
    engagement = pd.read_excel(file, sheet_name="App Engagement")
    users = pd.read_excel(file, sheet_name="User Profile")

    keep_cols = ["Activity_ID", "User_ID", "Date", "Workout_Type", "Duration_Minutes",
                 "Calories_Burned", "Steps_Count", "Heart_Rate_Avg", "Workout_Time_of_Day",
                 "Device_Used"]
    activity = activity[[c for c in keep_cols if c in activity.columns]].copy()

    activity["Date"] = pd.to_datetime(activity["Date"])
    engagement["Session_Date"] = pd.to_datetime(engagement["Session_Date"])
    users["App_Join_Date"] = pd.to_datetime(users["App_Join_Date"])

    # Recompute helper columns fresh (so the dashboard doesn't depend on
    # whatever was manually added in Excel)
    activity["Efficiency_Index"] = activity["Calories_Burned"] / activity["Duration_Minutes"]
    median_hr = activity["Heart_Rate_Avg"].median()
    activity["Intensity"] = np.where(
        activity["Heart_Rate_Avg"] >= median_hr, "High Intensity", "Low Intensity"
    )
    return activity, engagement, users


import os
if os.path.exists(DATA_PATH):
    activity_raw, engagement_raw, users_raw = load_data(DATA_PATH)
else:
    st.sidebar.warning("Default file not found — upload your dataset below.")
    uploaded = st.sidebar.file_uploader("Upload Combined Dataset (.xlsx)", type="xlsx")
    if uploaded is None:
        st.title("🏋️ FitTech Dashboard")
        st.info("Upload the Combined_Dataset_For_Project.xlsx file from the sidebar to begin.")
        st.stop()
    activity_raw, engagement_raw, users_raw = load_data(uploaded)

# ----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS (cascade: Users -> Activity / Engagement)
# ----------------------------------------------------------------------------
st.sidebar.header("🔎 Dashboard Filters")

age_opts = sorted(users_raw["Age_Group"].dropna().unique().tolist())
region_opts = sorted(users_raw["Region"].dropna().unique().tolist())
sub_opts = sorted(users_raw["Subscription_Type"].dropna().unique().tolist())

sel_age = st.sidebar.multiselect("Age Group", age_opts, default=age_opts)
sel_region = st.sidebar.multiselect("Region", region_opts, default=region_opts)
sel_sub = st.sidebar.multiselect("Subscription Type", sub_opts, default=sub_opts)

users = users_raw[
    users_raw["Age_Group"].isin(sel_age)
    & users_raw["Region"].isin(sel_region)
    & users_raw["Subscription_Type"].isin(sel_sub)
].copy()

valid_ids = set(users["User_ID"])
activity = activity_raw[activity_raw["User_ID"].isin(valid_ids)].copy()
engagement = engagement_raw[engagement_raw["User_ID"].isin(valid_ids)].copy()

st.sidebar.markdown("---")
st.sidebar.metric("Users after filters", f"{users['User_ID'].nunique():,}")
st.sidebar.metric("Activity records", f"{len(activity):,}")
st.sidebar.metric("Engagement sessions", f"{len(engagement):,}")

if activity.empty or engagement.empty or users.empty:
    st.warning("No data matches the current filters — widen your selection in the sidebar.")
    st.stop()

# Precomputed merges reused across many questions
activity_users = activity.merge(
    users[["User_ID", "Subscription_Type", "Age_Group", "Region", "Goal_Type", "Preferred_Workout_Type"]],
    on="User_ID", how="left", suffixes=("", "_u"),
)
engagement_users = engagement.merge(
    users[["User_ID", "Goal_Type", "Subscription_Type", "Age_Group", "Region"]],
    on="User_ID", how="left",
)

# ----------------------------------------------------------------------------
# 3. HELPERS
# ----------------------------------------------------------------------------
def insight(text):
    st.markdown(f"**Insight:** {text}")

def limitation(text):
    st.info(f"⚠️ **Data limitation:** {text}")

def kpi_row(items):
    cols = st.columns(len(items))
    for c, (label, value) in zip(cols, items):
        c.metric(label, value)

# ----------------------------------------------------------------------------
# 4. HEADER
# ----------------------------------------------------------------------------
st.title("🏋️ FitTech: Fitness App Usage & Calorie Burn Patterns")
st.caption("Assessing workout behaviour, engagement, and calorie burn patterns to drive personalised engagement.")

kpi_row([
    ("Total Users", f"{users['User_ID'].nunique():,}"),
    ("Total Workouts", f"{len(activity):,}"),
    ("Avg Calories / Workout", f"{activity['Calories_Burned'].mean():.0f}"),
    ("Total Engagement Sessions", f"{len(engagement):,}"),
])
st.markdown("---")

obj_tabs = st.tabs([
    "Objective 1: Workout Activity & Scheduling",
    "Objective 2: Subscription, Retention & Demographics",
    "Objective 3: Feature & Notification Engagement",
    "Objective 4: Efficiency & Hardware",
    "Objective 5: Personalisation & Recommendations",
])

# ============================================================================
# OBJECTIVE 1
# ============================================================================
with obj_tabs[0]:
    st.header("Objective 1: Evaluate Workout Activity, Calorie Burn & Scheduling Patterns")
    q1, q2, q3, q4, q5 = st.tabs(["Q1", "Q2", "Q3", "Q4", "Q5"])

    with q1:
        st.subheader("Which workout types yield the highest average calorie burn and total participation volume?")
        workout_analysis = (
            activity.groupby("Workout_Type")
            .agg(Average_Calories_Burned=("Calories_Burned", "mean"),
                 Total_Calories_Burned=("Calories_Burned", "sum"),
                 Participation_Volume=("Activity_ID", "count"))
            .sort_values("Average_Calories_Burned", ascending=False)
            .reset_index()
        )
        fig = px.bar(workout_analysis, x="Workout_Type", y="Average_Calories_Burned",
                     color="Participation_Volume", text_auto=".0f",
                     title="Average Calories Burned by Workout Type")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(workout_analysis.round(2), use_container_width=True)
        insight(f"**{workout_analysis.iloc[0]['Workout_Type']}** yields the highest average calorie burn, while "
                f"**{workout_analysis.sort_values('Participation_Volume', ascending=False).iloc[0]['Workout_Type']}** "
                f"has the highest participation volume.")

    with q2:
        st.subheader("What times of day correspond to peak activity levels across user segments?")
        split_by = st.radio("Segment by", ["Subscription_Type", "Age_Group", "Region"], horizontal=True, key="q2seg")
        pivot = pd.pivot_table(activity_users, index="Workout_Time_of_Day", columns=split_by,
                                values="Activity_ID", aggfunc="count", fill_value=0)
        fig = px.imshow(pivot, text_auto=True, aspect="auto",
                         title=f"Workout Time of Day vs {split_by}", color_continuous_scale="Purples")
        st.plotly_chart(fig, use_container_width=True)
        peak_time = activity["Workout_Time_of_Day"].value_counts()
        insight(f"Overall peak activity time is **{peak_time.idxmax()}** ({peak_time.max():,} workouts).")

    with q3:
        st.subheader("How does average workout duration vary by workout type and time slot?")
        duration_analysis = pd.pivot_table(activity, index="Workout_Type", columns="Workout_Time_of_Day",
                                            values="Duration_Minutes", aggfunc="mean")
        fig = px.imshow(duration_analysis.round(1), text_auto=True, aspect="auto",
                         title="Average Duration (min): Workout Type vs Time Slot", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(duration_analysis.round(2), use_container_width=True)
        insight("Longer average durations cluster in specific type/time combinations — useful for scheduling push reminders.")

    with q4:
        st.subheader("Which device types record the highest frequency of completed workouts?")
        device_completion = activity.merge(
            engagement[["User_ID", "Session_Date", "Workout_Completed"]], on="User_ID", how="inner"
        )
        summary = (
            device_completion.groupby("Device_Used")
            .agg(Total_Workout_Records=("Activity_ID", "count"),
                 Completed_Workouts=("Workout_Completed", lambda x: (x == "Yes").sum()))
        )
        summary["Completion_Rate_%"] = summary["Completed_Workouts"] / summary["Total_Workout_Records"] * 100
        summary = summary.sort_values("Completion_Rate_%", ascending=False).reset_index()
        fig = px.bar(summary, x="Device_Used", y="Completion_Rate_%", text_auto=".1f",
                     title="Completion Rate % by Device")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(summary.round(2), use_container_width=True)
        limitation("App Engagement is session-level and Activity is workout-level; joining only on User_ID can create "
                    "multiple matches. A shared session/activity key would make this precise.")

    with q5:
        st.subheader("Which combination of workout type and scheduled time slot has the lowest drop-off rate?")
        dropoff = (
            engagement.groupby("Feature_Used")
            .agg(Total_Sessions=("Session_ID", "count"),
                 Completed=("Workout_Completed", lambda x: (x == "Yes").sum()),
                 Not_Completed=("Workout_Completed", lambda x: (x == "No").sum()))
        )
        dropoff["Dropoff_Rate_%"] = dropoff["Not_Completed"] / dropoff["Total_Sessions"] * 100
        dropoff = dropoff.sort_values("Dropoff_Rate_%").reset_index()
        fig = px.bar(dropoff, x="Feature_Used", y="Dropoff_Rate_%", text_auto=".1f",
                     title="Drop-off Rate % by Feature (proxy)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dropoff.round(2), use_container_width=True)
        limitation("App Engagement does not contain Workout_Type or Workout_Time_of_Day, so the exact "
                    "Workout Type + Time Slot → Drop-off combination cannot be calculated directly. "
                    "Shown above is overall drop-off rate by feature as the closest available proxy.")

# ============================================================================
# OBJECTIVE 2
# ============================================================================
with obj_tabs[1]:
    st.header("Objective 2: Subscription, Retention & Demographics")
    q6, q7, q8, q9, q10 = st.tabs(["Q6", "Q7", "Q8", "Q9", "Q10"])

    with q6:
        st.subheader("How do Premium vs Free compare in daily activity levels and long-term retention?")
        user_activity = (
            activity.groupby("User_ID")
            .agg(Total_Workouts=("Activity_ID", "count"),
                 Total_Calories=("Calories_Burned", "sum"),
                 Active_Days=("Date", "nunique"))
            .reset_index()
        )
        user_subscription = users[["User_ID", "Subscription_Type"]].merge(
            user_activity, on="User_ID", how="left"
        ).fillna(0)
        subscription_activity = (
            user_subscription.groupby("Subscription_Type")
            .agg(Average_Workouts=("Total_Workouts", "mean"),
                 Average_Active_Days=("Active_Days", "mean"),
                 Average_Calories=("Total_Calories", "mean"))
            .reset_index()
        )
        fig = px.bar(subscription_activity.melt(id_vars="Subscription_Type"), x="Subscription_Type", y="value",
                     color="variable", barmode="group", title="Average Activity by Subscription Type")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(subscription_activity.round(2), use_container_width=True)
        pf = subscription_activity[subscription_activity["Subscription_Type"].isin(["Premium", "Free"])]
        if len(pf) == 2:
            insight("Premium vs Free comparison shown above — Premium users typically show higher average "
                    "workouts and active days, indicating stronger engagement tied to paid tiers.")

    with q7:
        st.subheader("What is the average consistency score across age demographics and regions?")
        limitation("Dataset has no Consistency_Score column. Shown below is a proxy: "
                    "Consistency = Active Days ÷ Days Since Joining.")
        last_activity_date = activity["Date"].max()
        uc = activity.groupby("User_ID").agg(Active_Days=("Date", "nunique")).reset_index()
        uc = uc.merge(users[["User_ID", "App_Join_Date", "Age_Group", "Region"]], on="User_ID", how="left")
        uc["Days_Since_Join"] = (last_activity_date - uc["App_Join_Date"]).dt.days + 1
        uc["Consistency_%"] = (uc["Active_Days"] / uc["Days_Since_Join"]) * 100
        c1, c2 = st.columns(2)
        with c1:
            by_age = uc.groupby("Age_Group")["Consistency_%"].mean().reset_index()
            st.plotly_chart(px.bar(by_age, x="Age_Group", y="Consistency_%", text_auto=".1f",
                                    title="Consistency % by Age Group"), use_container_width=True)
        with c2:
            by_region = uc.groupby("Region")["Consistency_%"].mean().reset_index()
            st.plotly_chart(px.bar(by_region, x="Region", y="Consistency_%", text_auto=".1f",
                                    title="Consistency % by Region"), use_container_width=True)

    with q8:
        st.subheader("How do primary fitness goals influence subscription conversion and churn?")
        goal_sub_pct = pd.crosstab(users["Goal_Type"], users["Subscription_Type"], normalize="index") * 100
        fig = px.bar(goal_sub_pct.reset_index().melt(id_vars="Goal_Type"), x="Goal_Type", y="value",
                     color="Subscription_Type", barmode="stack", title="Subscription Mix % by Goal Type")
        st.plotly_chart(fig, use_container_width=True)

        last_activity = activity.groupby("User_ID")["Date"].max().reset_index(name="Last_Activity_Date")
        user_churn = users.merge(last_activity, on="User_ID", how="left")
        dataset_end = activity["Date"].max()
        user_churn["Days_Inactive"] = (dataset_end - user_churn["Last_Activity_Date"]).dt.days
        user_churn["Churn_Proxy"] = np.where(user_churn["Days_Inactive"] > 30, "At Risk / Inactive", "Active")
        churn_pct = pd.crosstab(user_churn["Goal_Type"], user_churn["Churn_Proxy"], normalize="index") * 100
        st.dataframe(churn_pct.round(2), use_container_width=True)
        limitation("No explicit Churn column exists; churn is proxied as inactivity > 30 days since last workout.")

    with q9:
        st.subheader("Which region has the highest proportion of active Premium subscribers?")
        rp = users.copy()
        rp["Premium"] = rp["Subscription_Type"] == "Premium"
        summary = rp.groupby("Region").agg(Total_Users=("User_ID", "count"), Premium_Users=("Premium", "sum"))
        summary["Premium_%"] = summary["Premium_Users"] / summary["Total_Users"] * 100
        summary = summary.sort_values("Premium_%", ascending=False).reset_index()
        fig = px.bar(summary, x="Region", y="Premium_%", text_auto=".1f", title="Premium Subscriber % by Region")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(summary.round(2), use_container_width=True)
        insight(f"**{summary.iloc[0]['Region']}** has the highest proportion of Premium subscribers "
                f"({summary.iloc[0]['Premium_%']:.1f}%).")

    with q10:
        st.subheader("How does average active lifespan vary by demographic profile and fitness goal?")
        last_activity = activity.groupby("User_ID")["Date"].max().reset_index(name="Last_Activity_Date")
        lifespan = users.merge(last_activity, on="User_ID", how="left")
        lifespan["Active_Lifespan_Days"] = (lifespan["Last_Activity_Date"] - lifespan["App_Join_Date"]).dt.days
        by_age_goal = lifespan.groupby(["Age_Group", "Goal_Type"])["Active_Lifespan_Days"].mean().reset_index()
        fig = px.bar(by_age_goal, x="Age_Group", y="Active_Lifespan_Days", color="Goal_Type", barmode="group",
                     title="Average Active Lifespan (days) by Age Group & Goal")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(by_age_goal.sort_values("Active_Lifespan_Days", ascending=False).round(1),
                     use_container_width=True)

# ============================================================================
# OBJECTIVE 3
# ============================================================================
with obj_tabs[2]:
    st.header("Objective 3: App Feature Usage & Notification Engagement")
    q11, q12, q13, q14, q15 = st.tabs(["Q11", "Q12", "Q13", "Q14", "Q15"])

    with q11:
        st.subheader("Which core features drive the highest volume of total in-app activity?")
        feature_usage = (
            engagement.groupby("Feature_Used")
            .agg(Total_Sessions=("Session_ID", "count"),
                 Total_Session_Minutes=("Session_Duration_Minutes", "sum"),
                 Average_Session_Minutes=("Session_Duration_Minutes", "mean"))
            .sort_values("Total_Sessions", ascending=False).reset_index()
        )
        fig = px.bar(feature_usage, x="Feature_Used", y="Total_Sessions", text_auto=True,
                     title="Total Sessions by Feature")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(feature_usage.round(2), use_container_width=True)
        insight(f"**{feature_usage.iloc[0]['Feature_Used']}** drives the highest volume of in-app activity.")

    with q12:
        st.subheader("How does CTR of push notifications vary across app features?")
        ctr = engagement.groupby("Feature_Used").agg(
            Total_Notifications=("Notification_Clicked", "count"),
            Clicks=("Notification_Clicked", lambda x: (x == "Yes").sum()))
        ctr["CTR_%"] = ctr["Clicks"] / ctr["Total_Notifications"] * 100
        ctr = ctr.sort_values("CTR_%", ascending=False).reset_index()
        fig = px.bar(ctr, x="Feature_Used", y="CTR_%", text_auto=".1f", title="Notification CTR % by Feature")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(ctr.round(2), use_container_width=True)

    with q13:
        st.subheader("What is the correlation between Community engagement and overall monthly app retention?")
        eng = engagement.copy()
        eng["Month"] = eng["Session_Date"].dt.to_period("M").astype(str)
        monthly_active = eng.groupby("Month")["User_ID"].nunique().reset_index(name="Active_Users")
        community_monthly = (eng[eng["Feature_Used"] == "Community"]
                              .groupby("Month")["User_ID"].nunique().reset_index(name="Community_Users"))
        monthly_retention = monthly_active.merge(community_monthly, on="Month", how="left").fillna(0)
        monthly_retention["Community_Engagement_Rate"] = (
            monthly_retention["Community_Users"] / monthly_retention["Active_Users"]
        )
        fig = px.line(monthly_retention, x="Month", y=["Active_Users", "Community_Users"],
                       title="Monthly Active Users vs Community Users", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        corr = monthly_retention[["Community_Users", "Active_Users"]].corr().iloc[0, 1]
        insight(f"Correlation between Community users and total Active users: **r = {corr:.3f}**")

    with q14:
        st.subheader("How frequently do active users log Diet Log compared to Workout Tracker?")
        dw = engagement[engagement["Feature_Used"].isin(["Diet Log", "Workout Tracker"])]
        dw_summary = dw.groupby("Feature_Used").agg(
            Total_Uses=("Session_ID", "count"),
            Unique_Users=("User_ID", "nunique"),
            Average_Session_Duration=("Session_Duration_Minutes", "mean"))
        dw_summary["Uses_Per_User"] = dw_summary["Total_Uses"] / dw_summary["Unique_Users"]
        dw_summary = dw_summary.reset_index()
        fig = px.bar(dw_summary, x="Feature_Used", y="Uses_Per_User", text_auto=".2f",
                     title="Average Uses per User: Diet Log vs Workout Tracker")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dw_summary.round(2), use_container_width=True)

    with q15:
        st.subheader("Which feature triggers the highest average session duration?")
        feature_duration = (engagement.groupby("Feature_Used")["Session_Duration_Minutes"]
                             .mean().sort_values(ascending=False).reset_index())
        fig = px.bar(feature_duration, x="Feature_Used", y="Session_Duration_Minutes", text_auto=".1f",
                     title="Average Session Duration (min) by Feature")
        st.plotly_chart(fig, use_container_width=True)
        insight(f"**{feature_duration.iloc[0]['Feature_Used']}** triggers the highest average session duration "
                f"({feature_duration.iloc[0]['Session_Duration_Minutes']:.1f} min).")

# ============================================================================
# OBJECTIVE 4
# ============================================================================
with obj_tabs[3]:
    st.header("Objective 4: Workout Efficiency & Hardware Influence")
    q16, q17, q18, q19, q20 = st.tabs(["Q16", "Q17", "Q18", "Q19", "Q20"])

    with q16:
        st.subheader("What is the average workout efficiency index across age brackets?")
        age_eff = activity_users.groupby("Age_Group")["Efficiency_Index"].mean().sort_values(ascending=False).reset_index()
        fig = px.bar(age_eff, x="Age_Group", y="Efficiency_Index", text_auto=".2f",
                     title="Average Efficiency Index by Age Group")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Efficiency Index = Calories Burned ÷ Duration (Minutes)")

    with q17:
        st.subheader("How does primary access device impact workout completion rates?")
        device_activity = activity.groupby("Device_Used").agg(
            Total_Workouts=("Activity_ID", "count"),
            Average_Calories=("Calories_Burned", "mean"),
            Average_Duration=("Duration_Minutes", "mean")).reset_index()
        fig = px.bar(device_activity, x="Device_Used", y="Total_Workouts", text_auto=True,
                     title="Total Workouts by Device")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(device_activity.round(2), use_container_width=True)
        limitation("User Profile has no Primary Access Device field. For a true device-level completion rate, "
                    "device would need to sit in the same table as Workout_Completed via a reliable session key.")

    with q18:
        st.subheader("What is the relationship between wearable data and total calories burned?")
        c1, c2, c3 = st.columns(3)
        hr_r = activity[["Heart_Rate_Avg", "Calories_Burned"]].corr().iloc[0, 1]
        steps_r = activity[["Steps_Count", "Calories_Burned"]].corr().iloc[0, 1]
        dur_r = activity[["Duration_Minutes", "Calories_Burned"]].corr().iloc[0, 1]
        with c1:
            st.plotly_chart(px.scatter(activity, x="Heart_Rate_Avg", y="Calories_Burned", opacity=0.4,
                                        trendline="ols", title=f"Heart Rate vs Calories (r={hr_r:.3f})"),
                             use_container_width=True)
        with c2:
            st.plotly_chart(px.scatter(activity, x="Steps_Count", y="Calories_Burned", opacity=0.4,
                                        trendline="ols", title=f"Steps vs Calories (r={steps_r:.3f})"),
                             use_container_width=True)
        with c3:
            st.plotly_chart(px.scatter(activity, x="Duration_Minutes", y="Calories_Burned", opacity=0.4,
                                        trendline="ols", title=f"Duration vs Calories (r={dur_r:.3f})"),
                             use_container_width=True)
        insight("Duration typically shows the strongest relationship with calories burned, with heart rate and "
                "step count showing moderate positive relationships.")

    with q19:
        st.subheader("Do wearable users demonstrate higher efficiency than mobile-only users?")
        device_eff = activity.groupby("Device_Used").agg(
            Average_Efficiency=("Efficiency_Index", "mean"),
            Average_Calories=("Calories_Burned", "mean"),
            Average_Duration=("Duration_Minutes", "mean"),
            Workout_Count=("Activity_ID", "count")).sort_values("Average_Efficiency", ascending=False).reset_index()
        fig = px.bar(device_eff, x="Device_Used", y="Average_Efficiency", text_auto=".2f",
                     title="Average Efficiency Index by Device")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(device_eff.round(2), use_container_width=True)
        if "Smartwatch" in device_eff["Device_Used"].values and "Mobile" in device_eff["Device_Used"].values:
            sw = device_eff.loc[device_eff["Device_Used"] == "Smartwatch", "Average_Efficiency"].values[0]
            mb = device_eff.loc[device_eff["Device_Used"] == "Mobile", "Average_Efficiency"].values[0]
            insight("Smartwatch users have higher average efficiency than Mobile users." if sw > mb
                    else "Mobile users have higher average efficiency than Smartwatch users.")

    with q20:
        st.subheader("How does average workout duration affect efficiency for high vs low intensity?")
        duration_eff = activity.groupby("Intensity").agg(
            Average_Duration=("Duration_Minutes", "mean"),
            Average_Efficiency=("Efficiency_Index", "mean"),
            Average_Calories=("Calories_Burned", "mean")).reset_index()
        fig = px.bar(duration_eff, x="Intensity", y=["Average_Duration", "Average_Efficiency"], barmode="group",
                     title="Duration & Efficiency by Intensity")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(duration_eff.round(2), use_container_width=True)
        for intensity in ["High Intensity", "Low Intensity"]:
            subset = activity[activity["Intensity"] == intensity]
            if len(subset) > 1:
                r = subset[["Duration_Minutes", "Efficiency_Index"]].corr().iloc[0, 1]
                st.caption(f"{intensity}: Duration vs Efficiency r = {r:.3f}")

# ============================================================================
# OBJECTIVE 5
# ============================================================================
with obj_tabs[4]:
    st.header("Objective 5: Personalisation & Targeted Recommendations")
    q21, q22, q23, q24, q25 = st.tabs(["Q21", "Q22", "Q23", "Q24", "Q25"])

    with q21:
        st.subheader("How can historical calorie burn and activity preference suggest optimal workouts?")
        uwh = activity.groupby(["User_ID", "Workout_Type"]).agg(
            Average_Calories=("Calories_Burned", "mean"),
            Total_Workouts=("Activity_ID", "count"),
            Average_Duration=("Duration_Minutes", "mean")).reset_index()
        uwh["Workout_Score"] = uwh["Average_Calories"] * uwh["Total_Workouts"]
        recommended = (uwh.sort_values(["User_ID", "Workout_Score"], ascending=[True, False])
                       .groupby("User_ID").first().reset_index())
        recommendations = recommended.merge(
            users[["User_ID", "Preferred_Workout_Type", "Goal_Type"]], on="User_ID", how="left")
        st.dataframe(recommendations[["User_ID", "Workout_Type", "Preferred_Workout_Type", "Goal_Type",
                                       "Average_Calories", "Total_Workouts"]].head(50).round(1),
                     use_container_width=True)
        insight("Each user's recommended workout is the type that historically produced the strongest "
                "calorie burn and most frequent participation for them.")

    with q22:
        st.subheader("Which behavioral triggers best predict impending churn?")
        limitation("No explicit churn label exists — shown below is an inactivity-based At-Risk proxy (>30 days inactive).")
        last_act = activity.groupby("User_ID").agg(
            Last_Activity=("Date", "max"), Total_Workouts=("Activity_ID", "count"),
            Active_Days=("Date", "nunique")).reset_index()
        dataset_end = activity["Date"].max()
        churn = users.merge(last_act, on="User_ID", how="left")
        churn["Days_Inactive"] = (dataset_end - churn["Last_Activity"]).dt.days
        churn["At_Risk"] = np.where(churn["Days_Inactive"] > 30, "At Risk", "Active")
        trigger = churn.groupby("At_Risk").agg(
            Average_Days_Inactive=("Days_Inactive", "mean"),
            Average_Workouts=("Total_Workouts", "mean"),
            Average_Active_Days=("Active_Days", "mean")).reset_index()
        fig = px.bar(trigger.melt(id_vars="At_Risk"), x="variable", y="value", color="At_Risk", barmode="group",
                     title="At-Risk vs Active User Behaviour")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(trigger.round(2), use_container_width=True)

    with q23:
        st.subheader("Which personalized notification send-times produce highest CTR?")
        limitation("App Engagement contains Notification_Clicked but no notification send-time column, so this "
                    "exact question cannot be calculated from the current dataset. Add a Notification_Send_Time "
                    "column to enable this analysis.")

    with q24:
        st.subheader("How do targeted feature recommendations impact daily active engagement?")
        limitation("There is no field marking whether a feature was recommended/targeted, so recommended-vs-not "
                    "cannot be measured directly. Shown below is the daily active engagement baseline by feature.")
        eng = engagement.copy()
        eng["Day"] = eng["Session_Date"].dt.date
        daily = eng.groupby(["Day", "Feature_Used"]).agg(
            Active_Users=("User_ID", "nunique"), Sessions=("Session_ID", "count"),
            Total_Minutes=("Session_Duration_Minutes", "sum")).reset_index()
        fig = px.line(daily, x="Day", y="Active_Users", color="Feature_Used",
                      title="Daily Active Users by Feature")
        st.plotly_chart(fig, use_container_width=True)

    with q25:
        st.subheader("Which goal-oriented workout plans have highest completion and satisfaction across user tiers?")
        gc = engagement.merge(users[["User_ID", "Goal_Type", "Subscription_Type"]], on="User_ID", how="left")
        summary = gc.groupby(["Goal_Type", "Subscription_Type"]).agg(
            Total_Sessions=("Session_ID", "count"),
            Completed=("Workout_Completed", lambda x: (x == "Yes").sum()),
            Average_Rating=("User_Rating", "mean"))
        summary["Completion_Rate_%"] = summary["Completed"] / summary["Total_Sessions"] * 100
        summary = summary.reset_index().sort_values("Completion_Rate_%", ascending=False)
        fig = px.scatter(summary, x="Completion_Rate_%", y="Average_Rating", color="Goal_Type",
                          symbol="Subscription_Type", size="Total_Sessions",
                          title="Completion Rate vs Satisfaction by Goal & Subscription")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(summary.round(2), use_container_width=True)
        best_completion = summary.iloc[0]
        best_satisfaction = summary.sort_values("Average_Rating", ascending=False).iloc[0]
        insight(f"Highest completion: **{best_completion['Goal_Type']} / {best_completion['Subscription_Type']}** "
                f"({best_completion['Completion_Rate_%']:.1f}%). Highest satisfaction: "
                f"**{best_satisfaction['Goal_Type']} / {best_satisfaction['Subscription_Type']}** "
                f"({best_satisfaction['Average_Rating']:.2f}★).")

st.markdown("---")
st.caption("FitTech Dashboard — built from Objectives 1–5, Questions 1–25. Use the sidebar filters to explore subsets of users.")
