import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:cloud_functions/cloud_functions.dart';
import 'firebase_auth_service.dart';

class CloudFunctionsService {
  final FirebaseAuthService _authService;
  final FirebaseFunctions _functions = FirebaseFunctions.instance;

  CloudFunctionsService(this._authService);

  // Call a Cloud Function with authentication
  Future<dynamic> callFunction(String functionName, Map<String, dynamic> data) async {
    try {
      // Get the ID token
      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('User not authenticated');
      }

      // Call the function
      final result = await _functions.httpsCallable(functionName).call(data);
      return result.data;
    } catch (e) {
      rethrow;
    }
  }

  // Example of how to make an HTTP request to a Cloud Function with ID token
  Future<dynamic> callFunctionWithHttp(String functionUrl, Map<String, dynamic> data) async {
    try {
      // Get the ID token
      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('User not authenticated');
      }

      // Make the HTTP request with the ID token in the Authorization header
      final response = await http.post(
        Uri.parse(functionUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
        body: jsonEncode(data),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to call function: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }
}
