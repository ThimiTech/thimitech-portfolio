import { ref, computed } from "vue";

const accessToken = ref<string | null>(localStorage.getItem("access_token"));
const userEmail = ref<string | null>(localStorage.getItem("user_email"));
const loginOpen = ref(false);

export function useAuth() {
  const isLoggedIn = computed(() => !!accessToken.value);

  function setSession(access: string, refresh: string, email: string) {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    localStorage.setItem("user_email", email);
    accessToken.value = access;
    userEmail.value = email;
  }

  function setAccess(access: string) {
    localStorage.setItem("access_token", access);
    accessToken.value = access;
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_email");
    accessToken.value = null;
    userEmail.value = null;
  }

  function openLogin() {
    loginOpen.value = true;
  }

  function closeLogin() {
    loginOpen.value = false;
  }

  return {
    accessToken,
    userEmail,
    isLoggedIn,
    loginOpen,
    setSession,
    setAccess,
    logout,
    openLogin,
    closeLogin,
  };
}