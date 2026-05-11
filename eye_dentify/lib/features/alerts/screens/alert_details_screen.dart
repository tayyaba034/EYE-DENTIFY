import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/colors.dart';
import '../../../models/alert_model.dart';
import '../../../models/enums.dart';
import '../../../providers/auth_provider.dart';
import '../../../providers/alert_provider.dart';
import '../../../providers/detection_provider.dart';

class AlertDetailsScreen extends StatefulWidget {
  const AlertDetailsScreen({super.key});

  @override
  State<AlertDetailsScreen> createState() => _AlertDetailsScreenState();
}

class _AlertDetailsScreenState extends State<AlertDetailsScreen> {
  AlertModel? _alert;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final args = ModalRoute.of(context)?.settings.arguments;
    if (args is AlertModel) {
      _alert = args;
      context.read<AlertProvider>().markAsRead(args.alertId);
    }
  }

  @override
  Widget build(BuildContext context) {
    final alert = _alert;
    final alertProvider = context.watch<AlertProvider>();
    final detectionProvider = context.watch<DetectionProvider>();
    final authProvider = context.watch<AuthProvider>();

    if (alert == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Match Details'),
        ),
        body: const Center(child: Text('Alert details unavailable')),
      );
    }

    final detection = alert.detection;
    final verificationState = alertProvider.verificationState(alert);
    final matchPercentage =
        (detection?.combinedScore ?? 0).toStringAsFixed(0);
    final location = detection?.cameraLocation ?? 'Unknown Location';
    final time = detection?.detectionTimestamp.toLocal().toString() ??
        alert.alertTimestamp.toLocal().toString();
    final alertLevel = alert.alertLevel.displayName;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Match Details',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded,
              color: AppColors.bodyText, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Comparison Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(25),
                boxShadow: [
                  BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 20,
                      offset: const Offset(0, 10))
                ],
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('AI Comparison',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                            color: AppColors.successSoft,
                            borderRadius: BorderRadius.circular(20)),
                        child: Text('$matchPercentage%',
                            style: const TextStyle(
                                color: AppColors.success,
                                fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      _buildCompareImage(
                        'Reported',
                        detection?.originalPhotoUrl,
                        Icons.person_outline,
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 12),
                        child: Icon(Icons.bolt,
                            color: AppColors.warning, size: 30),
                      ),
                      _buildCompareImage(
                        'Detected',
                        detection?.snapshotUrl,
                        Icons.face_rounded,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Attributes Breakdown
            const Text('Attribute Analysis',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 12),
            _buildAttributeRow(
                'Facial Match',
                '${(detection?.faceMatchScore ?? 0).toStringAsFixed(0)}%',
                AppColors.success),
            _buildAttributeRow(
                'Clothing Color',
                detection?.colorMatchScore != null
                    ? '${detection!.colorMatchScore!.toStringAsFixed(0)}%'
                    : 'N/A',
                AppColors.primaryBlue),
            _buildAttributeRow(
                'Estimated Height',
                detection?.heightMatchScore != null
                    ? '${detection!.heightMatchScore!.toStringAsFixed(0)}%'
                    : 'N/A',
                AppColors.warning),

            const SizedBox(height: 24),

            // Live Feed Placeholder
            const Text('Live Camera Feed',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 12),
            Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(20),
                image: detection?.snapshotUrl != null
                    ? DecorationImage(
                        image: NetworkImage(detection!.snapshotUrl!),
                        fit: BoxFit.cover,
                        opacity: 0.6,
                      )
                    : null,
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  const Icon(Icons.play_circle_filled_rounded,
                      color: Colors.white, size: 60),
                  Positioned(
                    top: 12,
                    left: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                          color: Colors.red,
                          borderRadius: BorderRadius.circular(5)),
                      child: const Text('LIVE',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold)),
                    ),
                  ),
                  Positioned(
                    bottom: 12,
                    right: 12,
                    child: Text(location,
                        style:
                            const TextStyle(color: Colors.white, fontSize: 12)),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Escalation Level
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Row(
                children: [
                  const Icon(Icons.priority_high,
                      color: AppColors.warning, size: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Escalation Level',
                            style: TextStyle(fontWeight: FontWeight.bold)),
                        Text(
                          '$alertLevel • Seen ${alert.sightingsCount} time(s)',
                          style:
                              const TextStyle(color: Colors.grey, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            if ((alert.aiSummary ?? '').isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('AI Summary',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(
                      alert.aiSummary!,
                      style:
                          const TextStyle(color: AppColors.secondaryGray),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 24),

            // GPS Location
            const Text('GPS Location',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Row(
                children: [
                  const Icon(Icons.location_on_rounded,
                      color: AppColors.error, size: 30),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(location,
                            style: const TextStyle(fontWeight: FontWeight.bold)),
                        Text('Last updated $time',
                            style: const TextStyle(
                                color: Colors.grey, fontSize: 12)),
                      ],
                    ),
                  ),
                  OutlinedButton(
                    onPressed: (detection?.latitude != null &&
                            detection?.longitude != null)
                        ? () => _showLocationDialog(
                            context,
                            detection!.latitude!,
                            detection.longitude!,
                          )
                        : null,
                    style: OutlinedButton.styleFrom(
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    child: const Text('MAP'),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 30),

            // AI Status
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Row(
                children: [
                  Icon(
                    Icons.auto_awesome,
                    color: _statusColor(verificationState),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('AI Status: ${verificationState.displayName}',
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                        if (verificationState ==
                            VerificationState.pendingVerification)
                          const Text(
                            'Verifying with advanced AI… this may take a few seconds.',
                            style: TextStyle(
                                color: Colors.grey, fontSize: 12),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Actions
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: detectionProvider.isLoading
                        ? null
                        : () async {
                            final operatorId =
                                authProvider.currentUser?.userId;
                            if (operatorId == null) {
                              _showError(
                                  context, 'Operator session not available.');
                              return;
                            }

                            final payload = _buildDecisionPayload(
                              alert: alert,
                              decision: 'CONFIRM_MATCH',
                              operatorId: operatorId,
                            );

                            await alertProvider.queueDecision(
                              alert: alert,
                              targetStatus: AlertStatus.acknowledged,
                              finalize: () async {
                                await detectionProvider.confirmMatch(
                                  alert.alertId,
                                  decisionPayload: payload,
                                );
                                if (detectionProvider.errorMessage == null) {
                                  alertProvider.updateAlertStatus(
                                      alert.alertId, AlertStatus.acknowledged);
                                }
                              },
                            );

                            if (context.mounted) {
                              _showUndo(
                                context,
                                alertProvider,
                                alert.alertId,
                              );
                            }
                          },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.success,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15))),
                    child: const Text('CONFIRM MATCH'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: detectionProvider.isLoading
                        ? null
                        : () async {
                            final operatorId =
                                authProvider.currentUser?.userId;
                            if (operatorId == null) {
                              _showError(
                                  context, 'Operator session not available.');
                              return;
                            }

                            final payload = _buildDecisionPayload(
                              alert: alert,
                              decision: 'REJECT_FALSE_ALARM',
                              operatorId: operatorId,
                            );

                            await alertProvider.queueDecision(
                              alert: alert,
                              targetStatus: AlertStatus.dismissed,
                              finalize: () async {
                                await detectionProvider.rejectMatch(
                                  alert.alertId,
                                  decisionPayload: payload,
                                );
                                if (detectionProvider.errorMessage == null) {
                                  alertProvider.updateAlertStatus(
                                      alert.alertId, AlertStatus.dismissed);
                                }
                              },
                            );

                            if (context.mounted) {
                              _showUndo(
                                context,
                                alertProvider,
                                alert.alertId,
                              );
                            }
                          },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: AppColors.error,
                        side: const BorderSide(color: AppColors.error),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15))),
                    child: const Text('FALSE ALARM'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildCompareImage(String label, String? imageUrl, IconData icon) {
    return Expanded(
      child: Column(
        children: [
          Container(
            height: 120,
            width: double.infinity,
            decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(15)),
            child: imageUrl != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(15),
                    child: Image.network(
                      imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) =>
                          Icon(icon, color: Colors.grey[400], size: 40),
                    ),
                  )
                : Icon(icon, color: Colors.grey[400], size: 40),
          ),
          const SizedBox(height: 8),
          Text(label,
              style:
                  const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _buildAttributeRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(15)),
        child: Row(
          children: [
            Container(
                width: 4,
                height: 20,
                decoration: BoxDecoration(
                    color: color, borderRadius: BorderRadius.circular(10))),
            const SizedBox(width: 12),
            Text(label),
            const Spacer(),
            Text(value,
                style: TextStyle(fontWeight: FontWeight.bold, color: color)),
          ],
        ),
      ),
    );
  }

  Color _statusColor(VerificationState state) {
    switch (state) {
      case VerificationState.confirmedMatch:
        return AppColors.success;
      case VerificationState.rejectedFalseAlarm:
        return AppColors.error;
      case VerificationState.cloudTimeout:
        return AppColors.warning;
      case VerificationState.pendingVerification:
        return AppColors.primaryBlue;
      case VerificationState.preliminary:
        return AppColors.secondaryGray;
      case VerificationState.needsReview:
        return AppColors.warning;
    }
  }

  void _showLocationDialog(
      BuildContext context, double latitude, double longitude) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Camera Location'),
        content: Text('Lat: $latitude\nLng: $longitude'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showError(BuildContext context, String message) {
    if (message.isEmpty) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _showUndo(
      BuildContext context, AlertProvider provider, int alertId) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Decision recorded — Undo?'),
        action: SnackBarAction(
          label: 'UNDO',
          onPressed: () => provider.undoDecision(alertId),
        ),
        duration: const Duration(seconds: 10),
      ),
    );
  }

  Map<String, dynamic> _buildDecisionPayload({
    required AlertModel alert,
    required String decision,
    required String operatorId,
  }) {
    final detection = alert.detection;
    return {
      'alertId': alert.alertId,
      'decision': decision,
      'operatorId': operatorId,
      'timestamp': DateTime.now().toIso8601String(),
      'faceConfidence': detection?.faceMatchScore,
      'clothingConfidence': detection?.colorMatchScore,
      'snapshotUrl': detection?.snapshotUrl,
      'cameraId': detection?.cameraId,
    };
  }
}
