#!/bin/bash
set -e

DEPLOY_SUCCESS=false

# Funcao para garantir a limpeza mesmo em caso de erro
cleanup() {
    local exit_code=$?
    echo "Executando limpeza de seguranca (trap)..."
    if [ -n "$KEY_NAME" ]; then
        aws ec2 delete-key-pair --key-name $KEY_NAME >/dev/null 2>&1 || true
    fi
    rm -f ephemeral_key ephemeral_key.pub .env >/dev/null 2>&1 || true

    if [ "$DEPLOY_SUCCESS" != "true" ] && [ -n "$INSTANCE_ID" ]; then
        echo "ALERTA: O deploy falhou! Destruindo a maquina $INSTANCE_ID para evitar custos..."
        aws ec2 terminate-instances --instance-ids $INSTANCE_ID >/dev/null 2>&1 || true
        aws cloudwatch delete-alarms --alarm-names "mentoria-autodestruct-${INSTANCE_ID}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

# Configuracoes Iniciais
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
if [ "$VPC_ID" == "None" ]; then
    echo "Erro: Nenhuma VPC Default."
    exit 1
fi

SG_NAME="mentoria-ephemeral-sg"

if ! aws ec2 describe-security-groups --group-names $SG_NAME >/dev/null 2>&1; then
    echo "Criando Security Group..."
    SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME --description "SG Efemero para MentorIA" --vpc-id $VPC_ID --query "GroupId" --output text)
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0
else
    SG_ID=$(aws ec2 describe-security-groups --group-names $SG_NAME --query "SecurityGroups[0].GroupId" --output text)
fi

AMI_ID=$(aws ssm get-parameters --names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query "Parameters[0].Value" --output text)

# Limpeza de eventuais alarmes orfaos de deploys anteriores no CloudWatch
echo "Verificando e limpando eventuais alarmes orfaos de deploys anteriores..."
OLD_ALARMS=$(aws cloudwatch describe-alarms --alarm-name-prefix "mentoria-autodestruct-" --query "MetricAlarms[].AlarmName" --output text 2>/dev/null || true)
if [ -n "$OLD_ALARMS" ] && [ "$OLD_ALARMS" != "None" ]; then
    for alarm in $OLD_ALARMS; do
        old_inst=${alarm#"mentoria-autodestruct-"}
        state=$(aws ec2 describe-instances --instance-ids "$old_inst" --query "Reservations[0].Instances[0].State.Name" --output text 2>/dev/null || echo "terminated")
        if [ "$state" == "terminated" ] || [ -z "$state" ] || [ "$state" == "None" ]; then
            aws cloudwatch delete-alarms --alarm-names "$alarm" >/dev/null 2>&1 || true
        fi
    done
fi

# Gerar Chave SSH Temporaria com sufixo aleatorio para evitar colisao em re-runs
KEY_NAME="mentoria-key-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}-$(openssl rand -hex 4)"
ssh-keygen -t ed25519 -f ephemeral_key -N "" -q
aws ec2 import-key-pair --key-name $KEY_NAME --public-key-material fileb://ephemeral_key.pub

# Script simples e limpo (SEM SECRETS) para instalar Docker e garantir auto-destruicao da maquina
cat << 'EOF' > user-data.sh
#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# 1. Configurar servico e timer persistente do systemd para desligamento ACPI (12 horas)
# O systemd-timer invoca explicitamente /sbin/poweroff -f, emitindo o sinal ACPI de Poweroff
# que o hipervisor EC2 requer para acionar a terminacao (--instance-initiated-shutdown-behavior terminate).
# Nota: NUNCA usar 'shutdown -h', pois resulta em CPU halt e deixa a VM ligada na AWS gerando custos.
cat << 'EOF_SERVICE' > /etc/systemd/system/mentoria-autodestruct.service
[Unit]
Description=MentorIA Auto-Destruct Service (ACPI Poweroff to trigger EC2 termination)
DefaultDependencies=no
After=base.target

[Service]
Type=oneshot
ExecStart=/sbin/poweroff -f

[Install]
WantedBy=multi-user.target
EOF_SERVICE

cat << 'EOF_TIMER' > /etc/systemd/system/mentoria-autodestruct.timer
[Unit]
Description=Timer para auto-destruicao da maquina em 12 horas

[Timer]
OnBootSec=12h
Unit=mentoria-autodestruct.service

[Install]
WantedBy=timers.target
EOF_TIMER

systemctl daemon-reload
systemctl enable --now mentoria-autodestruct.timer

# 2. Configurar fallback no Cron (caso o timer do systemd sofra interferencia)
echo "@reboot root sleep 43200 && /sbin/poweroff -f" > /etc/cron.d/mentoria-autodestruct
chmod 644 /etc/cron.d/mentoria-autodestruct

# 3. Agendar via comando shutdown -P (Poweroff explicito, fallback adicional no SO)
shutdown -P +720 "MentorIA Auto-Destruct in 12 hours" || true

# 4. Instalar Docker e dependencias
apt-get update
apt-get install -y ca-certificates curl gnupg rsync
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

mkdir -p /home/ubuntu/mentoria
chown ubuntu:ubuntu /home/ubuntu/mentoria
EOF

echo "Lancando EC2 Instance (com volume gp3 de 30GB)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t3a.large \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --user-data file://user-data.sh \
    --instance-initiated-shutdown-behavior terminate \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=MentorIA-Ephemeral},{Key=AutoTerminate,Value=true},{Key=Project,Value=MentorIA},{Key=CreatedAt,Value=$(date -u +%Y-%m-%dT%H:%M:%SZ)},{Key=ManagedBy,Value=GitHubActions}]" \
    --query "Instances[0].InstanceId" \
    --output text)

AWS_REGION_NAME="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}"

echo "Configurando alarme no AWS CloudWatch para auto-terminacao via hipervisor (12 horas)..."
aws cloudwatch put-metric-alarm \
    --alarm-name "mentoria-autodestruct-${INSTANCE_ID}" \
    --alarm-description "Auto-destruir a instancia MentorIA apos 12 horas (garantia em nivel de hipervisor)" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Maximum \
    --period 3600 \
    --evaluation-periods 12 \
    --threshold 100 \
    --comparison-operator LessThanOrEqualToThreshold \
    --dimensions Name=InstanceId,Value=$INSTANCE_ID \
    --alarm-actions "arn:aws:automate:${AWS_REGION_NAME}:ec2:terminate" >/dev/null 2>&1 || echo "Aviso: Nao foi possivel criar alarme no CloudWatch (prosseguindo com timers no SO)."

echo "Aguardando maquina ligar..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "IP Publico: $PUBLIC_IP"
echo "Aguardando porta SSH (22) abrir..."
chmod 600 ephemeral_key
for i in {1..30}; do
  if nc -z -w 3 $PUBLIC_IP 22; then
    echo "Porta 22 detectada!"
    break
  fi
  sleep 5
done

echo "Aguardando inicializacao completa da maquina (cloud-init instalar Docker)..."
ssh -i ephemeral_key -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ConnectionAttempts=10 ubuntu@$PUBLIC_IP "cloud-init status --wait"

# Criar .env seguro localmente
DB_PASS=$(openssl rand -hex 16)
QDRANT_KEY=$(openssl rand -hex 16)
INTERNAL_KEY=$(openssl rand -hex 16)

# Copia o template original para garantir que NENHUMA variavel seja esquecida
cp .env.example .env

# Funcao helper para substituir valores no .env de forma segura e limpa
set_env() {
    local key=$1
    local val=$2
    if grep -q "^${key}=" .env; then
        sed -i "/^${key}=/d" .env
    fi
    echo "${key}=${val}" >> .env
}

# 1. Substituicoes de Infra e Seguranca (Geradas localmente)
set_env "WEB_PORT" "80"
set_env "POSTGRES_USER" "user"
set_env "POSTGRES_PASSWORD" "$DB_PASS"
set_env "DATABASE_URL" "postgresql+psycopg2://user:${DB_PASS}@db:5432/rag_db"
set_env "QDRANT_API_KEY" "$QDRANT_KEY"
set_env "QDRANT_URL" "http://vector_db:6333"
set_env "PASSWORD_PEPPER" "$APP_PASSWORD_PEPPER"
set_env "ENCRYPTION_SALT" "$APP_ENCRYPTION_SALT"
set_env "INTERNAL_API_KEY" "$INTERNAL_KEY"

# 2. Substituicoes Injetadas via GitHub Secrets
set_env "SECRET_KEY" "$APP_SECRET_KEY"
set_env "SYSTEM_USER_EMAIL" "$APP_SYSTEM_EMAIL"
set_env "SYSTEM_USER_PASSWORD" "$APP_SYSTEM_PASSWORD"
set_env "ADMIN_SLUG" "$APP_ADMIN_SLUG"
set_env "BACKUP_PASSPHRASE" "$APP_BACKUP_PASSPHRASE"

set_env "LLM_PROVIDER" "$APP_LLM_PROVIDER"
set_env "LLM_MODEL" "$APP_LLM_MODEL"
set_env "OPENAI_API_KEY" "$APP_OPENAI_API_KEY"
set_env "GEMINI_API_KEY" "$APP_GEMINI_API_KEY"

set_env "EMBEDDING_PROVIDER" "$APP_EMBEDDING_PROVIDER"
set_env "EMBEDDING_REMOTE_MODEL" "$APP_EMBEDDING_REMOTE_MODEL"
set_env "EMBEDDING_DIMENSION" "$APP_EMBEDDING_DIMENSION"

set_env "SMTP_SERVER" "$APP_SMTP_SERVER"
set_env "SMTP_PORT" "$APP_SMTP_PORT"
set_env "SMTP_USERNAME" "$APP_SMTP_USERNAME"
set_env "SMTP_PASSWORD" "$APP_SMTP_PASSWORD"
set_env "FROM_EMAIL" "$APP_FROM_EMAIL"

# 3. Configuracoes do Modo Efemero
set_env "FRONTEND_URL" "http://${PUBLIC_IP}"
set_env "NEXT_PUBLIC_API_BASE_URL" "http://${PUBLIC_IP}:8000/api/v1"
set_env "CORS_ALLOWED_ORIGINS" '["http://'${PUBLIC_IP}'", "http://'${PUBLIC_IP}':80", "http://'${PUBLIC_IP}':8000", "http://localhost:3000", "http://localhost:8000"]'
set_env "ENVIRONMENT" "production"
set_env "DEV_MODE" "False"
set_env "SKIP_PAYMENT" "True"
set_env "SECURE_COOKIES" "False"
set_env "FORCE_HTTPS" "False"
set_env "AUTO_RUN_SEEDER" "False"
set_env "ENABLE_API_DOCS" "False"
set_env "STT_ENABLED" "False"

 
echo "Enviando arquivos do projeto via SCP seguro..."
rsync -avz -e "ssh -i ephemeral_key -o StrictHostKeyChecking=no" --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude 'ephemeral_key*' ./ ubuntu@$PUBLIC_IP:/home/ubuntu/mentoria/

echo "Iniciando Docker na maquina..."
ssh -i ephemeral_key -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP "cd /home/ubuntu/mentoria && sudo docker compose up -d"

echo "Garantindo armamento do temporizador de auto-destruicao no sistema operacional (12h)..."
ssh -i ephemeral_key -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP "
    sudo systemctl daemon-reload
    sudo systemctl enable --now mentoria-autodestruct.timer
    sudo shutdown -P +720 'MentorIA Auto-Destruct in 12 hours' || true
    echo '=== STATUS DOS TIMERS ATIVOS NO SO ==='
    sudo systemctl list-timers mentoria-autodestruct.timer || true
"

echo "Finalizando script (o trap fara a limpeza das chaves SSH locais e temporarias)..."

echo "========================================================"
echo "DEPLOY EFEMERO CONCLUIDO COM SUCESSO!"
echo "URL da Aplicacao: http://$PUBLIC_IP"
echo "ID da Instancia: $INSTANCE_ID"
echo "Ciclo de vida maximo: 12 horas."
echo "Mecanismos de auto-destruicao armados:"
echo "  1. Alarme CloudWatch com acao de terminacao (Hipervisor AWS)"
echo "  2. Systemd Timer (mentoria-autodestruct.timer -> poweroff -f)"
echo "  3. Cron de seguranca (/etc/cron.d/mentoria-autodestruct)"
echo "Para destruir a qualquer momento sem esperar as 12h:"
echo "  Execute o workflow manual 'Destroy Ephemeral EC2' no GitHub Actions."
echo "========================================================"
DEPLOY_SUCCESS=true
