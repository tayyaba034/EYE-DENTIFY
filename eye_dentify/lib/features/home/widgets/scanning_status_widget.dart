import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../../../core/constants/colors.dart';
import '../../../models/enums.dart';

class ScanningStatusWidget extends StatefulWidget {
  final SystemStatus status;
  final int activeCameras;
  final int pendingAlerts;

  const ScanningStatusWidget({
    super.key,
    required this.status,
    required this.activeCameras,
    required this.pendingAlerts,
  });

  @override
  State<ScanningStatusWidget> createState() => _ScanningStatusWidgetState();
}

class _ScanningStatusWidgetState extends State<ScanningStatusWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller =
        AnimationController(vsync: this, duration: const Duration(seconds: 4))
          ..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor(widget.status);
    final statusLabel = widget.status.displayName;
    final subtitle = widget.status == SystemStatus.cloudDelay
        ? 'Verifying ${widget.pendingAlerts} alerts with advanced AI…'
        : 'AI scanning ${widget.activeCameras} nearby cameras…';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.darkBlueShield,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: AppColors.darkBlueShield.withValues(alpha: 0.3),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              AnimatedBuilder(
                animation: _controller,
                builder: (context, child) {
                  return Transform.rotate(
                    angle: _controller.value * 2 * math.pi,
                    child: Container(
                      width: 50,
                      height: 50,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                            color: Colors.white.withValues(alpha: 0.2),
                            width: 2),
                      ),
                      child: Stack(
                        children: [
                          Positioned(
                            top: 0,
                            left: 22,
                            child: Container(
                              width: 6,
                              height: 6,
                              decoration: const BoxDecoration(
                                  color: Colors.white, shape: BoxShape.circle),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
              const Icon(Icons.radar_rounded, color: Colors.white, size: 24),
            ],
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'System Status: $statusLabel',
                  style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16),
                ),
                Text(
                  subtitle,
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.7), fontSize: 13),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10)),
            child: Text(statusLabel.toUpperCase(),
                style: TextStyle(
                    color: statusColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 10)),
          ),
        ],
      ),
    );
  }

  Color _statusColor(SystemStatus status) {
    switch (status) {
      case SystemStatus.operational:
        return AppColors.success;
      case SystemStatus.cloudDelay:
        return AppColors.warning;
      case SystemStatus.offline:
        return AppColors.error;
    }
  }
}
