package com.dcsion3.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AmbientWidgetPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
