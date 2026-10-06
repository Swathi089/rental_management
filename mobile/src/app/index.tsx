import { useEffect, useRef, useState } from "react";
import { useRouter } from "expo-router";
import { AxiosError } from "axios";
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";

import API from "../api/api";
import { clearSession, getSession, saveSession, UserRole } from "../api/auth";

type LoginResponse = {
  access_token: string;
  user: {
    id: string;
    name: string;
    role: UserRole;
  };
};

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [error, setError] = useState("");
  const submitting = useRef(false);

  useEffect(() => {
    let mounted = true;

    getSession()
      .then((session) => {
        if (!mounted) return;
        if (!session.accessToken || !session.role) return;
        if (session.role === "OWNER") router.replace("/owner");
        else if (session.role === "TENANT") router.replace("/tenant");
        else void clearSession();
      })
      .finally(() => {
        if (mounted) setCheckingSession(false);
      });

    return () => {
      mounted = false;
    };
  }, [router]);

  const handleLogin = async () => {
    if (submitting.current) return;
    if (!email || !password) {
      setError("Enter your email and password.");
      return;
    }

    try {
      submitting.current = true;
      setLoading(true);
      setError("");

      const response = await API.post<LoginResponse>("/auth/login", {
        email,
        password,
      });

      const { access_token, user } = response.data;
      if (!access_token || !user?.id || !user.name || !user.role) {
        throw new Error("The server returned an incomplete login response.");
      }
      if (user.role !== "OWNER" && user.role !== "TENANT") {
        throw new Error("This account does not have a mobile dashboard.");
      }

      await saveSession(access_token, user);

      if (user.role === "OWNER") {
        router.replace("/owner");
      } else {
        router.replace("/tenant");
      }
    } catch (loginError) {
      const message = loginError instanceof AxiosError
        ? loginError.response?.data?.message || "Unable to connect to the server. Check your connection and try again."
        : loginError instanceof Error
          ? loginError.message
          : "Login failed. Please try again.";
      setError(message);
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  if (checkingSession) {
    return <View style={styles.loading}><ActivityIndicator size="large" color="#256b55" /></View>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.form}>
        <Text style={styles.eyebrow}>PRIVATE RENTAL MANAGEMENT</Text>
        <Text style={styles.title}>Welcome back</Text>
        <Text style={styles.subtitle}>Sign in to manage your rental account.</Text>

        <TextInput
          style={styles.input}
          placeholder="Email address"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          editable={!loading}
        />

        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="password"
          onSubmitEditing={handleLogin}
          editable={!loading}
        />

        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}

        <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
          {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.buttonText}>Sign in</Text>}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#f5f6f3",
  },
  form: {
    alignSelf: "center",
    width: "100%",
    maxWidth: 440,
    padding: 28,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#e1e5df",
    borderRadius: 8,
  },
  eyebrow: {
    color: "#256b55",
    fontSize: 11,
    fontWeight: "700",
    marginBottom: 12,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f5f6f3",
  },
  title: {
    color: "#18231e",
    fontSize: 30,
    fontWeight: "700",
    marginBottom: 6,
  },
  subtitle: {
    color: "#66716b",
    fontSize: 15,
    marginBottom: 26,
  },
  input: {
    height: 52,
    borderWidth: 1,
    borderColor: "#d9dfda",
    borderRadius: 6,
    paddingHorizontal: 14,
    marginBottom: 15,
    fontSize: 16,
    color: "#18231e",
  },
  button: {
    minHeight: 50,
    backgroundColor: "#256b55",
    borderRadius: 6,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 6,
  },
  buttonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  error: {
    color: "#a3312d",
    fontSize: 14,
    marginBottom: 12,
  },
});