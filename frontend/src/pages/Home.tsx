import { fr } from '@codegouvfr/react-dsfr'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Card } from '@codegouvfr/react-dsfr/Card'
import { useNavigate } from 'react-router-dom'

export const Home = () => {
    const navigate = useNavigate()

    return (
        <div className={fr.cx('fr-container', 'fr-py-6w')}>
            <div className={fr.cx('fr-grid-row', 'fr-grid-row--center')}>
                <div className={fr.cx('fr-col-12', 'fr-col-md-10', 'fr-col-lg-8')}>
                    <h1 className={fr.cx('fr-mb-2w')}>GRAAL</h1>
                    <p className={fr.cx('fr-text--lead', 'fr-mb-6w')}>
                        Gestion et Répartition Automatisée des Amendements Législatifs
                    </p>

                    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                        {/* Carte 1 : Traitement des amendements */}
                        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                            <Card
                                title="Traitement des amendements"
                                desc="Traitez et analysez automatiquement les amendements législatifs avec des fonctionnalités d'allotissement, d'attribution, de recherche de similarités et de génération de résumés."
                                start={
                                    <ul className={fr.cx('fr-badges-group')}>
                                        <li>
                                            <Badge severity="info" small>
                                                Allotissement
                                            </Badge>
                                        </li>
                                        <li>
                                            <Badge severity="info" small>
                                                Attribution
                                            </Badge>
                                        </li>
                                        <li>
                                            <Badge severity="info" small>
                                                Similarités
                                            </Badge>
                                        </li>
                                    </ul>
                                }
                                footer={
                                    <Button
                                        iconId="fr-icon-arrow-right-line"
                                        iconPosition="right"
                                        onClick={() => navigate('/processing')}
                                    >
                                        Commencer le traitement
                                    </Button>
                                }
                            />
                        </div>

                        {/* Carte 2 : Database Builder */}
                        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                            <Card
                                title="Database Builder"
                                desc="Construisez et gérez vos bases de données de similarités pour améliorer les résultats de recherche et optimiser le traitement des amendements."
                                start={
                                    <ul className={fr.cx('fr-badges-group')}>
                                        <li>
                                            <Badge severity="info" small>
                                                Base de données
                                            </Badge>
                                        </li>
                                        <li>
                                            <Badge severity="info" small>
                                                Gestion
                                            </Badge>
                                        </li>
                                    </ul>
                                }
                                footer={
                                    <Button
                                        iconId="fr-icon-arrow-right-line"
                                        iconPosition="right"
                                        onClick={() => navigate('/database')}
                                    >
                                        Ouvrir le Database Builder
                                    </Button>
                                }
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
