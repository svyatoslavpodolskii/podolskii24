import java.io.ByteArrayOutputStream
import java.util.Locale

plugins { id("com.android.application") }
android {
    sourceSets.getByName("main").res.setSrcDirs(listOf(layout.buildDirectory.dir("generated/runtime-res")))
    namespace = "dev.twentyfour.watchface"
    compileSdk = 36
    defaultConfig {
        applicationId = "dev.twentyfour.watchface"
        minSdk = 36
        targetSdk = 36
        versionCode = 15
        versionName = "5.4"
    }
    // Strip AGP-generated R classes as well: a WFF APK must contain no DEX.
    buildTypes {
        debug { isMinifyEnabled = true; isShrinkResources = false }
        release {
            isMinifyEnabled = true
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
// Original masters remain in src/main/res for reproducibility and byte-preservation
// tests. Package only images referenced by the optimized native scene or picker.
val stageRuntimeResources by tasks.registering(Sync::class) {
    from("src/main/res")
    into(layout.buildDirectory.dir("generated/runtime-res"))
    val used by lazy {
        val document = javax.xml.parsers.DocumentBuilderFactory.newInstance().newDocumentBuilder()
            .parse(file("src/main/res/raw/watchface.xml"))
        val result = mutableSetOf("preview")
        val elements = document.getElementsByTagName("*")
        for (i in 0 until elements.length) {
            val e = elements.item(i) as org.w3c.dom.Element
            for (a in listOf("resource", "icon")) if (e.hasAttribute(a)) result.add(e.getAttribute(a))
        }
        result
    }
    exclude { it.file.extension == "png" && it.file.nameWithoutExtension !in used }
    doLast {
        val decoded = layout.buildDirectory.dir("generated/runtime-res").get().asFile.walkTopDown()
            .filter { it.isFile && it.extension == "png" }.sumOf {
                val bitmap = javax.imageio.ImageIO.read(it)
                val bytes = bitmap.width.toLong() * bitmap.height * 4
                bitmap.flush()
                bytes
            }
        check(decoded <= 19000000L) { "Decoded PNG budget exceeded: $decoded bytes" }
    }
}
val validateWff by tasks.registering {
    doLast {
        check(rootProject.file("watchface/src/main/res/raw/watchface.xml").length() <= 10_000_000) {
            "WFF source exceeds the 10 MB limit"
        }
        val scene = javax.xml.parsers.DocumentBuilderFactory.newInstance().newDocumentBuilder()
            .parse(rootProject.file("watchface/src/main/res/raw/watchface.xml"))
        check(scene.getElementsByTagName("*").length <= 8000) { "WFF object budget exceeded" }
        check(rootProject.file("watchface/src/main/res/raw/watchface.xml").length() <= 800_000) { "Optimized WFF source budget exceeded" }
        val strings = javax.xml.parsers.DocumentBuilderFactory.newInstance().newDocumentBuilder()
            .parse(rootProject.file("watchface/src/main/res/values/strings.xml"))
        val labels = strings.getElementsByTagName("string")
        for (i in 0 until labels.length) String.format(Locale.ROOT, labels.item(i).textContent, 1)
        val output = ByteArrayOutputStream()
        project.exec {
            workingDir(rootProject.projectDir)
            commandLine("java", "-jar", "tools/wff-validator.jar", "4", "--stop-on-fail", "watchface/src/main/res/raw/watchface.xml")
            standardOutput = output
            errorOutput = output
        }
        val report = output.toString("UTF-8")
        logger.lifecycle(report)
        check(report.contains("PASSED") && !report.contains("FAILED") && !report.contains("SEVERE")) { "WFF v4 validation failed" }
    }
}
tasks.named("preBuild") { dependsOn(validateWff, stageRuntimeResources) }
tasks.register<Copy>("exportDebugApk") {
    dependsOn("assembleDebug")
    from(layout.buildDirectory.file("outputs/apk/debug/watchface-debug.apk"))
    into(rootProject.layout.projectDirectory.dir("dist"))
    rename { "Podolskii24-debug.apk" }
}
tasks.register<Copy>("exportReleaseApk") {
    dependsOn("assembleRelease")
    from(layout.buildDirectory.file("outputs/apk/release/watchface-release.apk"))
    into(rootProject.layout.projectDirectory.dir("dist"))
    rename { "Podolskii24-5.4.apk" }
}
