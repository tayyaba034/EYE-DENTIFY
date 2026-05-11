import 'package:intl/intl.dart';

class DateFormatter {
  static String dMMMyyyy(DateTime dateTime) {
    return DateFormat('d MMM, yyyy').format(dateTime);
  }

  static String hhmma(DateTime dateTime) {
    return DateFormat('hh:mm a').format(dateTime);
  }

  static String relative(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inSeconds < 60) {
      return '${difference.inSeconds}s ago';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return dMMMyyyy(dateTime);
    }
  }
}
