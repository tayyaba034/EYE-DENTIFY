import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'core/theme/app_theme.dart';
import 'core/network/api_client.dart';

import 'services/auth_service.dart';
import 'services/storage_service.dart';
import 'services/missing_person_service.dart';
import 'services/alert_service.dart';
import 'services/detection_service.dart';
import 'services/location_service.dart';
import 'services/camera_service.dart';
import 'services/notification_service.dart';

import 'providers/auth_provider.dart';
import 'providers/missing_person_provider.dart';
import 'providers/alert_provider.dart';
import 'providers/detection_provider.dart';
import 'providers/camera_provider.dart';
import 'providers/theme_provider.dart';
import 'providers/notification_provider.dart';

import 'features/auth/screens/splash_screen.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/auth/screens/signup_screen.dart';
import 'features/auth/screens/forgot_password_screen.dart';
import 'features/home/screens/home_screen.dart';
import 'features/report/screens/report_stepper_screen.dart';
import 'features/alerts/screens/alerts_list_screen.dart';
import 'features/profile/screens/profile_screen.dart';
import 'features/profile/screens/notification_settings.dart';
import 'features/cases/screens/my_cases_screen.dart';
import 'features/cases/screens/case_details_screen.dart';
import 'features/alerts/screens/alert_details_screen.dart';
import 'features/profile/screens/advanced_verification_screen.dart';
import 'features/profile/screens/change_password_screen.dart';
import 'features/profile/screens/two_factor_auth_screen.dart';
import 'features/profile/screens/location_sharing_screen.dart';
import 'features/profile/screens/blocked_users_screen.dart';
import 'features/help/screens/help_someone_screen.dart';

Future<void> _registerFcmToken() async {
  try {
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission();
    final token = await messaging.getToken();
    if (token == null) return;
    final apiClient = ApiClient(Dio(), storageService: StorageService());
    final notificationService = NotificationService(apiClient);
    await notificationService.registerDeviceToken(token);
  } catch (_) {}
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await _registerFcmToken();
  runApp(const EyeDentifyApp());
}

class EyeDentifyApp extends StatelessWidget {
  const EyeDentifyApp({super.key});

  @override
  Widget build(BuildContext context) {
    final dio = Dio();
    final storageService = StorageService();
    final apiClient = ApiClient(dio, storageService: storageService);

    final authService = AuthService(apiClient, storageService);
    final alertService = AlertService(apiClient);
    final missingPersonService = MissingPersonService(apiClient);
    final detectionService = DetectionService(apiClient);
    final cameraService = CameraService(apiClient);
    final locationService = LocationService();
    final notificationService = NotificationService(apiClient);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(
          create: (_) =>
              AuthProvider(authService, storageService)..checkAuthStatus(),
        ),
        ChangeNotifierProvider(
          create: (_) => MissingPersonProvider(missingPersonService),
        ),
        ChangeNotifierProvider(
          create: (_) => AlertProvider(alertService),
        ),
        ChangeNotifierProvider(
          create: (_) => DetectionProvider(detectionService),
        ),
        ChangeNotifierProvider(
          create: (_) => CameraProvider(cameraService),
        ),
        ChangeNotifierProvider(
          create: (_) => NotificationProvider(
            notificationService,
            storageService,
          )..initialize(),
        ),
        Provider(create: (_) => locationService),
        Provider(create: (_) => notificationService),
      ],
      child: const EyeDentifyAppView(),
    );
  }
}

class EyeDentifyAppView extends StatelessWidget {
  const EyeDentifyAppView({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return MaterialApp(
      title: 'EYE-DENTIFY',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: ThemeData.dark(),
      themeMode: themeProvider.themeMode,
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/login': (context) => const LoginScreen(),
        '/signup': (context) => const SignupScreen(),
        '/forgot-password': (context) => const ForgotPasswordScreen(),
        '/home': (context) => const HomeScreen(),
        '/report': (context) => const ReportStepperScreen(),
        '/cases': (context) => const MyCasesScreen(),
        '/alerts': (context) => const AlertsListScreen(),
        '/profile': (context) => const ProfileScreen(),
        '/notifications': (context) => const NotificationSettingsScreen(),
        '/alert-details': (context) => const AlertDetailsScreen(),
        '/case-details': (context) => const CaseDetailsScreen(),
        '/help-someone': (context) => const HelpSomeoneScreen(),
        '/advanced-verification': (context) =>
            const AdvancedVerificationScreen(),
        '/change-password': (context) => const ChangePasswordScreen(),
        '/2fa': (context) => const TwoFactorAuthScreen(),
        '/location-sharing': (context) => const LocationSharingScreen(),
        '/blocked-users': (context) => const BlockedUsersScreen(),
      },
    );
  }
}
