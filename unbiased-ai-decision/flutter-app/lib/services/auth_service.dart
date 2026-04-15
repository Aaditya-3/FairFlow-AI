import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'firebase_service.dart';

class AuthSession {
  const AuthSession({
    required this.uid,
    this.email,
    this.name,
    required this.isGuest,
    required this.isFirebaseBacked,
  });

  final String uid;
  final String? email;
  final String? name;
  final bool isGuest;
  final bool isFirebaseBacked;
}

class AuthService {
  AuthService._() {
    _firebaseSubscription = _auth.authStateChanges().listen((user) {
      if (_localGuestSession != null && user == null) {
        _emitCurrentSession();
        return;
      }

      if (user != null) {
        _localGuestSession = null;
      }
      _emitCurrentSession();
    });
  }

  static final AuthService instance = AuthService._();

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final StreamController<AuthSession?> _sessionController =
      StreamController<AuthSession?>.broadcast();
  late final StreamSubscription<User?> _firebaseSubscription;
  AuthSession? _localGuestSession;
  Map<String, dynamic>? _preloadedGuestAudit;

  Stream<AuthSession?> get authStateChanges async* {
    yield currentSession;
    yield* _sessionController.stream;
  }

  User? get currentUser => _auth.currentUser;

  AuthSession? get currentSession =>
      _localGuestSession ?? _mapFirebaseUser(_auth.currentUser);

  bool get isGuest => currentSession?.isGuest ?? false;

  Map<String, dynamic>? consumePreloadedGuestAudit() {
    final payload = _preloadedGuestAudit;
    _preloadedGuestAudit = null;
    return payload;
  }

  AuthSession? _mapFirebaseUser(User? user) {
    if (user == null) {
      return null;
    }

    return AuthSession(
      uid: user.uid,
      email: user.email,
      name: user.displayName,
      isGuest: user.isAnonymous,
      isFirebaseBacked: true,
    );
  }

  void _activateLocalGuestSession() {
    _localGuestSession = const AuthSession(
      uid: 'guest-demo',
      name: 'Guest',
      isGuest: true,
      isFirebaseBacked: false,
    );
  }

  void _emitCurrentSession() {
    if (!_sessionController.isClosed) {
      _sessionController.add(currentSession);
    }
  }

  Future<UserCredential> signInWithGoogle() async {
    _localGuestSession = null;
    if (kIsWeb) {
      final provider = GoogleAuthProvider();
      provider.addScope('email');
      return _auth.signInWithPopup(provider);
    }

    final googleUser = await GoogleSignIn(scopes: ['email']).signIn();
    if (googleUser == null) {
      throw Exception('Google sign-in was cancelled.');
    }

    final googleAuth = await googleUser.authentication;
    final credential = GoogleAuthProvider.credential(
      accessToken: googleAuth.accessToken,
      idToken: googleAuth.idToken,
    );
    return _auth.signInWithCredential(credential);
  }

  Future<Map<String, dynamic>?> signInAsGuest() async {
    try {
      await _auth.signInAnonymously();
      _localGuestSession = null;
      try {
        _preloadedGuestAudit = await FirebaseService.instance.fetchSampleAudit();
      } catch (_) {
        _preloadedGuestAudit = FirebaseService.instance.localSampleAudit();
      }
      _preloadedGuestAudit ??= FirebaseService.instance.localSampleAudit();
    } catch (_) {
      _activateLocalGuestSession();
      _preloadedGuestAudit = FirebaseService.instance.localSampleAudit();
    }
    _emitCurrentSession();
    return _preloadedGuestAudit;
  }

  Future<void> signOut() async {
    _localGuestSession = null;
    _preloadedGuestAudit = null;
    await Future.wait([
      GoogleSignIn().signOut().catchError((_) {}),
      _auth.signOut().catchError((_) {}),
    ]);
    _emitCurrentSession();
  }
}
