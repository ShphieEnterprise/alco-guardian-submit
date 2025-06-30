import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../home_screen.dart';
import 'login_screen.dart';
import 'register_screen.dart';

enum AuthState {
  login,
  register,
}

class AuthWrapper extends StatefulWidget {
  const AuthWrapper({super.key});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  AuthState _authState = AuthState.login;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: _auth.authStateChanges(),
      builder: (context, snapshot) {
        // If the user is logged in, show the home screen
        if (snapshot.hasData) {
          return const HomeScreen();
        }

        // Otherwise, show the login or register screen
        switch (_authState) {
          case AuthState.login:
            return LoginScreen(
              onRegisterPressed: () {
                setState(() {
                  _authState = AuthState.register;
                });
              },
              onLoginResult: (success) {
                // No need to do anything here as the StreamBuilder
                // will automatically update when auth state changes
              },
            );
          case AuthState.register:
            return RegisterScreen(
              onLoginPressed: () {
                setState(() {
                  _authState = AuthState.login;
                });
              },
              onRegisterResult: (success) {
                // No need to do anything here as the StreamBuilder
                // will automatically update when auth state changes
              },
            );
        }
      },
    );
  }
}
