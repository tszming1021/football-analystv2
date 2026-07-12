import { AuthForm } from "../../components/AuthForm";

export const dynamic = "force-dynamic";

export default function RegisterPage() {
  const captcha = String(Math.floor(1000 + Math.random() * 9000));
  return <AuthForm initialMode="register" initialCaptcha={captcha} />;
}
