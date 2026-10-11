package com.punkshows.app

import android.app.Activity
import android.view.ViewGroup.LayoutParams
import android.webkit.WebView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        val web = WebView(this)
        web.loadUrl("https://17h1nk.github.io/punkshows/")
        addContentView(
            web,
            LayoutParams(android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.MATCH_PARENT),
        )
    }
}
