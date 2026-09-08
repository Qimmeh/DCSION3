package com.dcsion3.app;

import android.content.Context;
import android.content.SharedPreferences;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Capacitor bridge plugin to synchronize workload, battery,
 * and focus block data from the Web App to the Android Homescreen Widget.
 */
@CapacitorPlugin(name = "AmbientWidget")
public class AmbientWidgetPlugin extends Plugin {

    @PluginMethod
    public void updateWidgetData(PluginCall call) {
        Context context = getContext();
        SharedPreferences prefs = context.getSharedPreferences(AmbientWidgetProvider.PREFS_NAME, Context.MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();

        if (call.hasOption("batteryCapacity")) {
            Integer batteryCapacity = call.getInt("batteryCapacity");
            if (batteryCapacity != null) {
                editor.putInt("battery_capacity", batteryCapacity);
            }
        }
        if (call.hasOption("batteryStatus")) {
            String batteryStatus = call.getString("batteryStatus");
            if (batteryStatus != null) {
                editor.putString("battery_status", batteryStatus);
            }
        }
        if (call.hasOption("burnoutRiskLevel")) {
            String burnoutRiskLevel = call.getString("burnoutRiskLevel");
            if (burnoutRiskLevel != null) {
                editor.putString("burnout_risk_level", burnoutRiskLevel);
            }
        }
        if (call.hasOption("capacityLoad")) {
            Integer capacityLoad = call.getInt("capacityLoad");
            if (capacityLoad != null) {
                editor.putInt("capacity_load", capacityLoad);
            }
        }
        if (call.hasOption("focusTitle")) {
            String focusTitle = call.getString("focusTitle");
            if (focusTitle != null) {
                editor.putString("focus_title", focusTitle);
            }
        }
        if (call.hasOption("focusTime")) {
            String focusTime = call.getString("focusTime");
            if (focusTime != null) {
                editor.putString("focus_time", focusTime);
            }
        }
        editor.apply();

        // Refresh all widgets on homescreen
        AmbientWidgetProvider.updateAllWidgets(context);

        call.resolve();
    }
}
