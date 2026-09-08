package com.dcsion3.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.widget.RemoteViews;
import android.widget.Toast;

/**
 * Ambient Workload Manager Homescreen Gadget (AppWidgetProvider).
 * Displays glanceable battery health, capacity load, burnout risk,
 * next focus block, and allows quick one-tap actions from the homescreen.
 */
public class AmbientWidgetProvider extends AppWidgetProvider {

    public static final String ACTION_EXTEND_TASK = "com.dcsion3.app.ACTION_EXTEND_TASK";
    public static final String ACTION_TAKE_REST = "com.dcsion3.app.ACTION_TAKE_REST";
    public static final String ACTION_REFRESH_WIDGET = "com.dcsion3.app.ACTION_REFRESH_WIDGET";
    public static final String PREFS_NAME = "DCSION3_Ambient_Widget_Prefs";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    public static void updateAppWidget(Context context, AppWidgetManager appWidgetManager, int appWidgetId) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);

        int batteryCapacity = prefs.getInt("battery_capacity", 85);
        String batteryStatus = prefs.getString("battery_status", "Healthy");
        String burnoutRiskLevel = prefs.getString("burnout_risk_level", "Low");
        int capacityLoad = prefs.getInt("capacity_load", 68);
        String focusTitle = prefs.getString("focus_title", "Deep Work: Active Task");
        String focusTime = prefs.getString("focus_time", "Today • Ambient Mode");

        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.ambient_workload_widget);

        // Battery badge
        views.setTextViewText(R.id.widget_battery_badge, "🔋 " + batteryCapacity + "% " + batteryStatus);

        // Burnout risk badge & color
        views.setTextViewText(R.id.widget_burnout_badge, "● " + burnoutRiskLevel + " Risk");
        int riskColor = Color.parseColor("#4ADE80"); // Low (green)
        if ("Moderate".equalsIgnoreCase(burnoutRiskLevel)) {
            riskColor = Color.parseColor("#FACC15"); // Yellow
        } else if ("High".equalsIgnoreCase(burnoutRiskLevel)) {
            riskColor = Color.parseColor("#FB923C"); // Orange
        } else if ("Critical".equalsIgnoreCase(burnoutRiskLevel)) {
            riskColor = Color.parseColor("#F87171"); // Red
        }
        views.setTextColor(R.id.widget_burnout_badge, riskColor);

        // Capacity load
        views.setTextViewText(R.id.widget_load_value, capacityLoad + "%");

        // Focus title & time
        views.setTextViewText(R.id.widget_focus_title, focusTitle);
        views.setTextViewText(R.id.widget_focus_time, focusTime);

        // Tap on widget root or Open button -> Launch MainActivity
        Intent launchIntent = new Intent(context, MainActivity.class);
        launchIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPendingIntent = PendingIntent.getActivity(
                context,
                0,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_root, openPendingIntent);
        views.setOnClickPendingIntent(R.id.widget_btn_open, openPendingIntent);

        // Quick action: +30m Extension
        Intent extendIntent = new Intent(context, AmbientWidgetProvider.class);
        extendIntent.setAction(ACTION_EXTEND_TASK);
        PendingIntent extendPendingIntent = PendingIntent.getBroadcast(
                context,
                101,
                extendIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_btn_extend, extendPendingIntent);

        // Quick action: Take Rest
        Intent restIntent = new Intent(context, AmbientWidgetProvider.class);
        restIntent.setAction(ACTION_TAKE_REST);
        PendingIntent restPendingIntent = PendingIntent.getBroadcast(
                context,
                102,
                restIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_btn_rest, restPendingIntent);

        // Instruct the widget manager to update the widget
        appWidgetManager.updateAppWidget(appWidgetId, views);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);

        String action = intent.getAction();
        if (ACTION_EXTEND_TASK.equals(action)) {
            // Save state or notify user
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            int currentLoad = prefs.getInt("capacity_load", 68);
            prefs.edit().putInt("capacity_load", Math.min(100, currentLoad + 5)).apply();
            Toast.makeText(context, "DCSION3: Task extended by +30 mins", Toast.LENGTH_SHORT).show();
            updateAllWidgets(context);
        } else if (ACTION_TAKE_REST.equals(action)) {
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            int battery = prefs.getInt("battery_capacity", 85);
            prefs.edit()
                    .putInt("battery_capacity", Math.min(100, battery + 5))
                    .putString("focus_title", "Rest / Recovery Break")
                    .putString("focus_time", "Active • 15 min rest")
                    .apply();
            Toast.makeText(context, "DCSION3: Recovery session initiated", Toast.LENGTH_SHORT).show();
            updateAllWidgets(context);
        } else if (ACTION_REFRESH_WIDGET.equals(action)) {
            updateAllWidgets(context);
        }
    }

    public static void updateAllWidgets(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        ComponentName widgetComponent = new ComponentName(context, AmbientWidgetProvider.class);
        int[] ids = manager.getAppWidgetIds(widgetComponent);
        if (ids != null && ids.length > 0) {
            for (int id : ids) {
                updateAppWidget(context, manager, id);
            }
        }
    }
}
