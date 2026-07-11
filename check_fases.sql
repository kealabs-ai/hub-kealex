-- Verificar processos e fases
SELECT 
    p.id as processo_id,
    p.numero,
    p.titulo,
    COUNT(f.id) as total_fases
FROM processos p
LEFT JOIN fases f ON p.id = f.processo_id
GROUP BY p.id, p.numero, p.titulo
ORDER BY p.created_at DESC
LIMIT 10;

-- Verificar fases de um processo específico (substitua o ID)
-- SELECT * FROM fases WHERE processo_id = 'SEU_PROCESSO_ID' ORDER BY ordem;
