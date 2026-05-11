import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/foundation.dart';

class LocationService {
  LocationService();

  /// Checks if location permissions are granted and requests them if not.
  /// Returns true if permissions are granted, false otherwise.
  Future<bool> checkLocationPermissions() async {
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  /// Gets the current device location.
  /// Returns a [Position] if successful, throws an error otherwise.
  Future<Position> getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled.');
    }

    bool permissionsGranted = await checkLocationPermissions();
    if (!permissionsGranted) {
      throw Exception('Location permissions are denied.');
    }

    try {
      return await Geolocator.getCurrentPosition();
    } catch (e) {
      debugPrint('Error getting current location: $e');
      throw Exception('Could not retrieve current location.');
    }
  }

  /// Converts coordinates (latitude, longitude) to a list of [Placemark]s.
  Future<List<Placemark>> getAddressFromCoordinates(
      double latitude, double longitude) async {
    try {
      return await placemarkFromCoordinates(latitude, longitude);
    } catch (e) {
      debugPrint('Error getting address from coordinates: $e');
      throw Exception('Could not retrieve address for the given coordinates.');
    }
  }

  /// Converts an address string to coordinates (latitude, longitude).
  /// Returns a map containing 'latitude' and 'longitude' if successful.
  Future<Map<String, double>?> getCoordinatesFromAddress(String address) async {
    try {
      final locations = await locationFromAddress(address);
      if (locations.isNotEmpty) {
        return {
          'latitude': locations.first.latitude,
          'longitude': locations.first.longitude,
        };
      }
      return null;
    } catch (e) {
      debugPrint('Geocoding error: $e');
      return null;
    }
  }

  /// Formats a list of [Placemark]s into a readable address string.
  String formatPlacemarkAddress(List<Placemark> placemarks) {
    if (placemarks.isEmpty) return 'No address found';
    final placemark = placemarks.first;
    final parts = <String>[];

    if (placemark.street?.isNotEmpty ?? false) parts.add(placemark.street!);
    if (placemark.locality?.isNotEmpty ?? false) parts.add(placemark.locality!);
    if (placemark.administrativeArea?.isNotEmpty ?? false) {
      parts.add(placemark.administrativeArea!);
    }
    if (placemark.country?.isNotEmpty ?? false) parts.add(placemark.country!);

    return parts.join(', ');
  }
}
