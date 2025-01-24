# -*- coding: utf-8 -*-
"""streamlit_app.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1GoLEexdRXoq2OCd3kZe69hMS4eLDq_1D
"""

import hopsworks
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import joblib
from urllib.error import URLError

# Cache data fetching to optimize app performance
@st.cache_data
def get_data():
    # Set the Hopsworks API key
    os.environ["HOPSWORKS_API_KEY"] = "ir5PKrvMxVGQtr4I.OJAzB9b685t2LvfMHguGosCsipkeOyV0XSRsiz5ia81FyxNkSlgHW5eGY6b3W99O"  # Replace with your API key

    # Login to Hopsworks
    project = hopsworks.login(project="MyAQI_Predictor")
    fs = project.get_feature_store()

    # Get the Feature Group for your AQI predictions
    fg = fs.get_feature_group("aqi_featuregroup", version=2)  # Replace with your feature group name/version
    df = fg.read(online=True)
    return df, project

# Streamlit app logic
try:
    # Fetch data and project from Hopsworks
    df, project = get_data()

    # Streamlit app title and description
    st.title("Air Quality Index Prediction")
    st.write("Welcome to the AQI Prediction App!")

    # Historical AQI Trends
    try:
        # Plot historical AQI data
        fig = px.line(df, x="date", y="main_aqi", title="Historical AQI Trends", labels={"main_aqi": "AQI", "date": "Date"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig)

    except Exception as e:
        st.error("Error displaying historical AQI trends.")
        st.write(e)

    # Load the current AQI data from the feature store
    try:
        # Get the latest data from the DataFrame
        latest_data = df.iloc[-1]  # Get the last row of the DataFrame

        # Display current AQI
        st.metric(label="Current AQI", value=f"{latest_data['main_aqi']:.2f}")

        # Highlight AQI levels based on the 1-5 range
        if latest_data["main_aqi"] >= 4:
            st.write("🚨 **High AQI**: Stay Home!")
        elif latest_data["main_aqi"] == 3:
            st.write("⚠️ **Moderate AQI**: Sensitive groups take precautions.")
        else:
            st.write("✅ **Good AQI**: Air quality is perfect!")

    except Exception as e:
        st.error("Error loading current AQI data. Check your feature store setup.")
        st.write(e)

    # Load the model from the Hopsworks Model Registry
    try:
        mr = project.get_model_registry()
        model = mr.get_model("air_quality_prediction_model", version=1)  # Replace with your model name/version
        model_dir = model.download()
        rfg_model = joblib.load(f"{model_dir}/model.pkl")  # Adjust path if needed

        # Generate predictions for the next 3 days
        today = datetime.datetime.now()
        future_dates = [today + datetime.timedelta(days=i) for i in range(1, 4)]

        # Fetch the most recent data from the feature store to use as input
        latest_features = pd.DataFrame([latest_data])  # Use your fetched `latest_data`

        # Remove `main_aqi` from input data to match model's features
        latest_features = latest_features.drop(columns=["main_aqi"])

        # Replicate the latest features for the next 3 days
        input_data = pd.concat([latest_features] * 3, ignore_index=True)

        # Adjust specific features for each day (e.g., incrementing dates)
        for i in range(3):
            input_data.loc[i, "day"] = (latest_data["day"] + i + 1) % 31 or 31
            input_data.loc[i, "day_of_week"] = (latest_data["day_of_week"] + i + 1) % 7
            input_data.loc[i, "is_weekend"] = 1 if input_data.loc[i, "day_of_week"] in [5, 6] else 0
            input_data.loc[i, "aqi_lag_1"] = latest_data["main_aqi"]  # Use today's AQI as lag for Day 1
            input_data.loc[i, "aqi_lag_2"] = input_data.loc[i, "aqi_lag_1"]  # Propagate for Day 2
            input_data.loc[i, "aqi_lag_3"] = input_data.loc[i, "aqi_lag_2"]  # Propagate for Day 3

        # Predict the AQI for the next 3 days
        predictions = rfg_model.predict(input_data)

        # Display predictions
        st.subheader("Predicted AQI for the Next 3 Days")
        for date, pred in zip(future_dates, predictions):
            aqi_level = "High" if pred > 4 else "Moderate" if pred >= 3 else "Good"
            st.write(f"{date.strftime('%Y-%m-%d')}: {pred:.2f} (Level: {aqi_level})")

        # AQI Predictions Visualization
        st.subheader("AQI Predictions Visualization")
        prediction_df = pd.DataFrame({
            "Date": future_dates,
            "Predicted AQI": predictions,
            "Level": ["High" if p > 4 else "Moderate" if p >= 3 else "Good" for p in predictions]
        })

        # Plot AQI predictions
        fig_pred = px.line(prediction_df, x="Date", y="Predicted AQI", title="Predicted AQI for the Next 3 Days", markers=True, labels={"Predicted AQI": "AQI"})
        fig_pred.update_traces(line_color="blue")
        fig_pred.update_layout(showlegend=False)
        st.plotly_chart(fig_pred)

    except Exception as e:
        st.error("Error loading model or generating predictions. Check your model setup.")
        st.write(e)

except Exception as e:
    st.error("Error connecting to Hopsworks or fetching data. Please check your configuration.")
    st.write(e)

# Footer
st.write("Data provided by OpenMeteo and OpenWeather APIs. Powered by Hopsworks.")

