import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:provider/provider.dart';
import '../../../models/alert_model.dart';
import '../../../providers/alert_provider.dart';
import '../../../providers/camera_provider.dart';

class CameraHeatmapScreen extends StatefulWidget {
  const CameraHeatmapScreen({super.key});

  @override
  State<CameraHeatmapScreen> createState() => _CameraHeatmapScreenState();
}

class _CameraHeatmapScreenState extends State<CameraHeatmapScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CameraProvider>().fetchCameras();
      context.read<AlertProvider>().syncSnapshot(force: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    final cameraProvider = context.watch<CameraProvider>();
    final alertProvider = context.watch<AlertProvider>();

    final markers = <Marker>{
      ...cameraProvider.cameras.map((camera) {
        final alertCount = _alertCountForCamera(alertProvider.alerts, camera.id);
        final lastDetection = _lastDetectionTime(alertProvider.alerts, camera.id);
        return Marker(
          markerId: MarkerId(camera.id),
          position: LatLng(camera.latitude, camera.longitude),
          infoWindow: InfoWindow(
            title: camera.name ?? camera.type,
            snippet:
                '${camera.location}\nAlerts: $alertCount\nLast detection: ${lastDetection ?? 'N/A'}',
          ),
        );
      }),
    };

    final circles = <Circle>{
      ...cameraProvider.cameras.map((camera) {
        final density = _alertCountForCamera(alertProvider.alerts, camera.id);
        final radius = 80.0 + (density * 35.0);
        final alpha = (40 + density * 20).clamp(40, 180).toInt();
        return Circle(
          circleId: CircleId('heat-${camera.id}'),
          center: LatLng(camera.latitude, camera.longitude),
          radius: radius,
          fillColor: Colors.red.withAlpha(alpha),
          strokeWidth: 0,
        );
      }),
    };

    return Scaffold(
      appBar: AppBar(title: const Text('Camera Heatmap')),
      body: GoogleMap(
        initialCameraPosition: const CameraPosition(
          target: LatLng(33.6844, 73.0479),
          zoom: 11,
        ),
        markers: markers,
        circles: circles,
        myLocationEnabled: true,
        myLocationButtonEnabled: true,
      ),
    );
  }

  int _alertCountForCamera(List<AlertModel> alerts, String cameraId) {
    return alerts.where((a) {
      final id = a.detection?.cameraId?.toString();
      return id == cameraId;
    }).length;
  }

  String? _lastDetectionTime(List<AlertModel> alerts, String cameraId) {
    DateTime? latest;
    for (final alert in alerts) {
      final id = alert.detection?.cameraId?.toString();
      if (id != cameraId) continue;
      final dt = alert.detection?.detectionTimestamp;
      if (dt == null) continue;
      if (latest == null || dt.isAfter(latest)) latest = dt;
    }
    if (latest == null) return null;
    return latest.toLocal().toIso8601String();
  }
}
