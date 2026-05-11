import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/colors.dart';
import '../../../providers/alert_provider.dart';
import '../../../providers/camera_provider.dart';
import '../../../providers/missing_person_provider.dart';
import '../../cases/screens/my_cases_screen.dart';
import '../../alerts/screens/alerts_list_screen.dart';
import '../../profile/screens/profile_screen.dart';
import '../widgets/welcome_card.dart';
import '../widgets/stat_card.dart';
import '../widgets/recent_alert_card.dart';
import '../widgets/scanning_status_widget.dart';
import '../../help/screens/help_someone_screen.dart';
import 'camera_heatmap_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;
  late final List<Widget> _screens;

  @override
  void initState() {
    super.initState();
    _screens = [
      HomeContent(
          onTabChange: (index) => setState(() => _currentIndex = index)),
      const MyCasesScreen(),
      const CameraHeatmapScreen(),
      const HelpSomeoneScreen(),
      const AlertsListScreen(),
      const ProfileScreen(),
    ];

    // Fetch initial data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final alertProvider = context.read<AlertProvider>();
      alertProvider.initializeRealtime();
      alertProvider.fetchMyAlerts();
      final missingPersonProvider = context.read<MissingPersonProvider>();
      missingPersonProvider.initializeRealtime();
      missingPersonProvider.fetchMyCases();
      missingPersonProvider.fetchActiveCases();
      context.read<CameraProvider>().fetchCameras();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppColors.primaryBlue,
        unselectedItemColor: Colors.grey,
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        items: const [
          BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined),
              activeIcon: Icon(Icons.home),
              label: 'Home'),
          BottomNavigationBarItem(
              icon: Icon(Icons.assignment_outlined),
              activeIcon: Icon(Icons.assignment),
              label: 'My Cases'),
          BottomNavigationBarItem(
              icon: Icon(Icons.map_outlined),
              activeIcon: Icon(Icons.map),
              label: 'Map'),
          BottomNavigationBarItem(
              icon: Icon(Icons.volunteer_activism_outlined),
              activeIcon: Icon(Icons.volunteer_activism),
              label: 'Community'),
          BottomNavigationBarItem(
              icon: Icon(Icons.notifications_outlined),
              activeIcon: Icon(Icons.notifications),
              label: 'Alerts'),
          BottomNavigationBarItem(
              icon: Icon(Icons.person_outline),
              activeIcon: Icon(Icons.person),
              label: 'Profile'),
        ],
      ),
    );
  }
}

class HomeContent extends StatelessWidget {
  final Function(int)? onTabChange;
  const HomeContent({super.key, this.onTabChange});

  @override
  Widget build(BuildContext context) {
    final alertProvider = context.watch<AlertProvider>();
    final cameraProvider = context.watch<CameraProvider>();
    final missingPersonProvider = context.watch<MissingPersonProvider>();

    final activeCasesCount = missingPersonProvider.myCases
        .where((c) => c.status.name == 'active')
        .length
        .toString();
    final alertsTodayCount = alertProvider.alertsTodayCount.toString();
    final activeCamerasCount = cameraProvider.activeCameras.toString();
    final pendingAlertsCount = alertProvider.pendingVerificationCount;
    final confirmedAlertsCount = alertProvider.confirmedAlertsCount.toString();

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          'Home',
          style:
              TextStyle(color: AppColors.bodyText, fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        leading: const Padding(
          padding: EdgeInsets.all(8.0),
          child: CircleAvatar(
            backgroundColor: AppColors.darkBlueShield,
            child: Icon(Icons.security, color: Colors.white, size: 20),
          ),
        ),
        actions: [
          Stack(
            children: [
              IconButton(
                onPressed: () {
                  onTabChange?.call(4);
                },
                icon: const Icon(Icons.notifications_none_rounded,
                    color: AppColors.bodyText),
              ),
              if (alertProvider.alerts.isNotEmpty)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: const BoxDecoration(
                        color: Colors.red, shape: BoxShape.circle),
                    constraints:
                        const BoxConstraints(minWidth: 12, minHeight: 12),
                    child: Text(
                      alertProvider.alerts.length.toString(),
                      style: const TextStyle(color: Colors.white, fontSize: 8),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await Future.wait([
            context.read<AlertProvider>().fetchMyAlerts(),
            context.read<MissingPersonProvider>().fetchMyCases(),
          ]);
        },
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const WelcomeCard(),
              const SizedBox(height: 20),
              ScanningStatusWidget(
                status: alertProvider.systemStatus,
                activeCameras: cameraProvider.activeCameras,
                pendingAlerts: pendingAlertsCount,
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  StatCard(
                      title: 'Active Cameras',
                      value: activeCamerasCount,
                      icon: Icons.videocam_rounded),
                  StatCard(
                      title: 'Alerts Today',
                      value: alertsTodayCount,
                      icon: Icons.notification_important_rounded),
                  StatCard(
                      title: 'Verifying',
                      value: pendingAlertsCount.toString(),
                      icon: Icons.autorenew_rounded),
                  StatCard(
                      title: 'Confirmed',
                      value: confirmedAlertsCount,
                      icon: Icons.check_circle_rounded),
                ],
              ),
              const SizedBox(height: 30),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Recent Alerts',
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppColors.bodyText),
                  ),
                  TextButton(
                    onPressed: () {
                      onTabChange?.call(4);
                    },
                    child: const Text('View All',
                        style: TextStyle(color: AppColors.primaryBlue)),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              if (alertProvider.isLoading)
                const Center(child: CircularProgressIndicator())
              else if (alertProvider.alerts.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 20),
                    child: Text('No recent alerts found'),
                  ),
                )
              else
                ...alertProvider.alerts
                    .take(3)
                    .map((alert) => RecentAlertCard(alert: alert)),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.pushNamed(context, '/report'),
        backgroundColor: AppColors.primaryBlue,
        icon: const Icon(Icons.add_rounded, color: Colors.white),
        label: const Text('REPORT MISSING',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}
